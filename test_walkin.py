import os
import django

# Initialize Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bus_booking.settings")
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from api.models import Route, Booking, SeatLayout

def test_walkin_booking():
    from django.conf import settings
    if 'testserver' not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append('testserver')

    print("==================================================")
    print("             WALK-IN API BOOKING TEST             ")
    print("==================================================")

    # 1. Fetch Staff User
    User = get_user_model()
    try:
        admin_user = User.objects.get(email='admin@busbook.com')
        print(f"1. Authenticating as admin staff: {admin_user.email}")
    except User.DoesNotExist:
        print("Admin user not found!")
        return

    client = APIClient()
    client.force_authenticate(user=admin_user)

    # 2. Get Route ID 1 and inspect starting state
    route = Route.objects.get(id=1)
    print(f"\n2. Target Route: {route.source} -> {route.destination} on {route.date}")
    print(f"   Original Available Seats: {route.available_seats}")
    
    test_seat = 'A4'
    seat = SeatLayout.objects.get(route=route, seat_number=test_seat)
    print(f"   Target Seat {test_seat} status: is_booked={seat.is_booked}")
    
    if seat.is_booked:
        print(f"   [Error] Seat {test_seat} is already booked! Releasing it first to run clean test...")
        seat.is_booked = False
        seat.save()
        route.available_seats += 1
        route.save()
        route.refresh_from_db()
        seat.refresh_from_db()
        print(f"   Route Reset: Available Seats={route.available_seats}, Seat {test_seat} is_booked={seat.is_booked}")

    # 3. Create Walk-in Guest Booking via API Call
    print(f"\n3. Submitting walk-in booking API request for Seat {test_seat} without account...")
    payload = {
        "route_id": route.id,
        "travel_date": str(route.date),
        "passengers": [
            {
                "name": "Walkin Guest Passenger",
                "age": 30,
                "gender": "Male",
                "seat_number": test_seat
            }
        ],
        "is_walkin": True,
        "guest_name": "Walk-in Guest Buyer",
        "guest_phone": "0300-9876543",
        "guest_email": "walkin_buyer@domain.com"
    }
    
    res = client.post('/api/bookings/create/', payload, format='json')
    print(f"   Response Status Code: {res.status_code}")
    print(f"   Response Data: {res.data}")
    
    if res.status_code != 201:
        print("   [Failure] API request failed!")
        return
        
    booking_id = res.data['data']['booking_id']
    print(f"   SUCCESS: Walk-in Booking created with ID {booking_id}")

    # 4. Verify Walk-in Booking State in DB
    print(f"\n4. Checking created Booking {booking_id} in Database:")
    booking = Booking.objects.get(booking_id=booking_id)
    print(f"   - Associated User: {booking.user} (Should be None/Null for walk-in)")
    print(f"   - Guest Name: '{booking.guest_name}'")
    print(f"   - Guest Phone: '{booking.guest_phone}'")
    print(f"   - Guest Email: '{booking.guest_email}'")
    print(f"   - Booking Status: '{booking.status}' (Should be CONFIRMED)")
    print(f"   - Payment Status: '{booking.payment_status}' (Should be PAID)")

    # 5. Verify Seat Reservation State
    route.refresh_from_db()
    seat.refresh_from_db()
    print(f"\n5. Verifying Seat and Capacity Locking:")
    print(f"   - Updated Route Available Seats: {route.available_seats} (Should decrease by 1)")
    print(f"   - Seat {test_seat} is_booked status: {seat.is_booked} (Should be True)")
    
    # 6. Delete booking to verify cleanup trigger
    print(f"\n6. Deleting Booking {booking_id} to test seat release trigger...")
    booking.delete()
    
    route.refresh_from_db()
    seat.refresh_from_db()
    print(f"   - Restored Route Available Seats: {route.available_seats}")
    print(f"   - Restored Seat {test_seat} is_booked status: {seat.is_booked} (Should be False)")

    print("\n==================================================")
    print("        WALK-IN API BOOKING TEST SUCCESSFUL!       ")
    print("==================================================")

if __name__ == '__main__':
    test_walkin_booking()
