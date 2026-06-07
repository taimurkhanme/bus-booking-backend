import os
import django
import datetime
from django.utils import timezone

# Initialize Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bus_booking.settings")
django.setup()

from api.models import User, Bus, Route, Booking, SeatLayout, Passenger

def run_tests():
    print("==================================================")
    print("              DATABASE DIAGNOSTIC TEST            ")
    print("==================================================")

    # 1. Inspect Users
    print("\n[1] INSPECTING USERS:")
    users = User.objects.all()
    print(f"Total Users: {users.count()}")
    for u in users:
        print(f" - Email: '{u.email}' (Username: '{u.username}', Staff: {u.is_staff}, Superuser: {u.is_superuser})")

    # 2. Inspect Buses
    print("\n[2] INSPECTING BUSES:")
    buses = Bus.objects.all()
    print(f"Total Buses: {buses.count()}")
    for bus in buses:
        print(f" - ID {bus.id}: {bus.name} ({bus.bus_number}), Total Seats: {bus.total_seats}")

    # 3. Inspect Routes
    print("\n[3] INSPECTING ROUTES:")
    routes = Route.objects.all()
    print(f"Total Routes: {routes.count()}")
    for r in routes:
        print(f" - ID {r.id}: {r.source} -> {r.destination} on {r.date} (seats={r.available_seats}, active={r.is_active})")

    # 4. Inspect Bookings
    print("\n[4] INSPECTING BOOKINGS:")
    bookings = Booking.objects.all()
    print(f"Total Bookings: {bookings.count()}")
    for b in bookings:
        passengers = b.passengers.all()
        seats = [p.seat_number for p in passengers]
        print(f" - Booking {b.booking_id}: status={b.status}, payment_status={b.payment_status}, user={b.user.email}, date={b.travel_date}, seats={seats}")

    # 5. Test Status Change Synchronization
    print("\n[5] TESTING BOOKING CANCEL SYNCHRONIZATION:")
    # Find a non-cancelled booking
    pending_booking = Booking.objects.exclude(status='CANCELLED').first()
    if pending_booking:
        print(f"Original Booking State:")
        print(f" - Booking ID: {pending_booking.booking_id}")
        print(f" - Status: {pending_booking.status}")
        
        route = pending_booking.route
        print(f" - Route ID: {route.id} ({route.source} -> {route.destination})")
        print(f" - Route Available Seats before cancel: {route.available_seats}")
        
        passengers = pending_booking.passengers.all()
        seat_numbers = [p.seat_number for p in passengers]
        print(f" - Passenger seats: {seat_numbers}")
        
        # Check seat layouts status before cancel
        seats_before = SeatLayout.objects.filter(route=route, seat_number__in=seat_numbers)
        print(" - Seat states before cancel:")
        for s in seats_before:
            print(f"   * Seat {s.seat_number}: is_booked={s.is_booked}")
            
        print("\nChanging booking status to 'CANCELLED' in database (simulating Django Admin)...")
        pending_booking.status = 'CANCELLED'
        pending_booking.save()
        
        # Refresh and verify
        pending_booking.refresh_from_db()
        route.refresh_from_db()
        seats_after = SeatLayout.objects.filter(route=route, seat_number__in=seat_numbers)
        
        print("\nUpdated Booking State:")
        print(f" - Status: {pending_booking.status}")
        print(f" - Route Available Seats after cancel: {route.available_seats}")
        print(" - Seat states after cancel:")
        for s in seats_after:
            print(f"   * Seat {s.seat_number}: is_booked={s.is_booked}")
            
        # Revert back to test reverse sync
        print("\nReverting booking status back to 'CONFIRMED' (simulating Admin restore)...")
        pending_booking.status = 'CONFIRMED'
        pending_booking.save()
        
        pending_booking.refresh_from_db()
        route.refresh_from_db()
        seats_reverted = SeatLayout.objects.filter(route=route, seat_number__in=seat_numbers)
        print(f"Reverted Route Available Seats: {route.available_seats}")
        print("Reverted Seat states:")
        for s in seats_reverted:
            print(f"   * Seat {s.seat_number}: is_booked={s.is_booked}")
    else:
        print("No active bookings found in the database to test cancel synchronization.")

    # 6. Test Route Addition
    print("\n[6] TESTING ROUTE ADDITION AND SEAT GENERATION:")
    today = timezone.localtime().date()
    test_date = today + datetime.timedelta(days=5)
    test_source = "TestLahore"
    test_dest = "TestKarachi"
    
    # Check if test route already exists, if so delete it
    Route.objects.filter(source=test_source, destination=test_dest, date=test_date).delete()
    
    bus = Bus.objects.first()
    if bus:
        print(f"Adding new route: {test_source} -> {test_dest} on {test_date} for bus {bus.name}")
        new_route = Route.objects.create(
            bus=bus,
            source=test_source,
            destination=test_dest,
            date=test_date,
            departure_time=timezone.make_aware(datetime.datetime.combine(test_date, datetime.time(hour=9))),
            arrival_time=timezone.make_aware(datetime.datetime.combine(test_date, datetime.time(hour=17))),
            price=2500.00
        )
        print(f"New Route ID: {new_route.id}")
        print(f"Route Available Seats: {new_route.available_seats}")
        
        # Check if SeatLayouts were generated
        layouts_count = SeatLayout.objects.filter(route=new_route).count()
        print(f"Seat layouts auto-created for new route: {layouts_count}")
        
        # Verify Search Query matches it
        print("\nVerifying search query functionality for the new route:")
        matching_routes = Route.objects.filter(
            source__iexact=test_source,
            destination__iexact=test_dest,
            date=test_date,
            available_seats__gt=0,
            is_active=True
        )
        print(f"Search query matching routes count: {matching_routes.count()}")
        if matching_routes.count() > 0:
            print("SUCCESS: Search query correctly matches the newly created route!")
        else:
            print("FAILURE: Search query did NOT match the newly created route!")
            
        # Clean up test route
        new_route.delete()
        print("Test route cleaned up.")
    else:
        print("No bus found in database to create test route.")

if __name__ == "__main__":
    run_tests()
