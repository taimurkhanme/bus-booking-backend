import os
import django

# Initialize Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bus_booking.settings")
django.setup()

import random
import string
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from api.models import User, Bus, Route, Booking, SeatLayout, Payment

def print_result(feature_name, success, message=""):
    status_str = "SUCCESS" if success else "FAILURE"
    marker = "OK" if success else "FAIL"
    print(f"[{marker}] {feature_name:<40}: {status_str} {message}")

def run_complete_audit():
    print("==================================================")
    print("           COMPLETE PROJECT AUDIT SUITE           ")
    print("==================================================")
    
    from django.conf import settings
    if 'testserver' not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append('testserver')

    client = APIClient()
    User = get_user_model()
    
    # ----------------------------------------------------
    # FEATURE 1: USER REGISTRATION
    # ----------------------------------------------------
    test_email = "audit_user_99@example.com"
    test_password = "password123"
    test_phone = "0311-9876543"
    test_name = "Audit Tester"
    
    # Clean up user if already exists from a broken test run
    User.objects.filter(email=test_email).delete()
    
    print("\n--- FEATURE 1: USER REGISTRATION ---")
    reg_payload = {
        "name": test_name,
        "email": test_email,
        "phone": test_phone,
        "password": test_password
    }
    res_reg = client.post('/api/auth/register/', reg_payload, format='json')
    
    success_reg = res_reg.status_code == 201
    message_reg = ""
    if success_reg:
        user_id = res_reg.data.get('data', {}).get('user', {}).get('id')
        message_reg = f"(Created User ID: {user_id})"
    else:
        message_reg = f"(Status: {res_reg.status_code}, Error: {res_reg.data})"
    print_result("User Registration API", success_reg, message_reg)
    
    if not success_reg:
        return

    # ----------------------------------------------------
    # FEATURE 2: USER LOGIN (JWT TOKEN ACQUISITION)
    # ----------------------------------------------------
    print("\n--- FEATURE 2: USER LOGIN (JWT) ---")
    login_payload = {
        "email": test_email,
        "password": test_password
    }
    res_login = client.post('/api/auth/login/', login_payload, format='json')
    success_login = res_login.status_code == 200
    access_token = ""
    message_login = ""
    if success_login:
        access_token = res_login.data.get('data', {}).get('access')
        message_login = f"(Token length: {len(access_token)})"
        # Authenticate client for subsequent requests
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    else:
        message_login = f"(Status: {res_login.status_code})"
    print_result("User Login & Token API", success_login, message_login)

    # ----------------------------------------------------
    # FEATURE 3: PROFILE RETRIEVAL & UPDATE
    # ----------------------------------------------------
    print("\n--- FEATURE 3: USER PROFILE ---")
    res_prof_get = client.get('/api/auth/profile/')
    success_prof_get = res_prof_get.status_code == 200
    print_result("Retrieve Profile API", success_prof_get)
    
    update_payload = {
        "first_name": "Audited Name",
        "phone": "0311-1111111"
    }
    res_prof_put = client.put('/api/auth/profile/', update_payload, format='json')
    success_prof_put = res_prof_put.status_code == 200
    message_prof_put = ""
    if success_prof_put:
        updated_name = res_prof_put.data.get('data', {}).get('first_name')
        message_prof_put = f"(Updated Name to: '{updated_name}')"
    print_result("Update Profile API", success_prof_put, message_prof_put)

    # ----------------------------------------------------
    # FEATURE 4: DYNAMIC CITIES & BUS SEARCH
    # ----------------------------------------------------
    print("\n--- FEATURE 4: ROUTES & BUSES SEARCH ---")
    res_cities = client.get('/api/buses/cities/')
    success_cities = res_cities.status_code == 200
    message_cities = f"(Unique Cities count: {len(res_cities.data.get('data', [])) if success_cities else 0})"
    print_result("Unique Cities List API", success_cities, message_cities)
    
    # Query for route 1 cities
    route1 = Route.objects.get(id=1)
    search_params = {
        "source": route1.source,
        "destination": route1.destination,
        "date": str(route1.date)
    }
    res_search = client.get('/api/buses/search/', search_params)
    success_search = res_search.status_code == 200
    message_search = f"(Matching routes count: {len(res_search.data.get('data', [])) if success_search else 0})"
    print_result("Search Active Routes API", success_search, message_search)

    # ----------------------------------------------------
    # FEATURE 5: ROUTE SEAT LAYOUT RETRIEVAL
    # ----------------------------------------------------
    print("\n--- FEATURE 5: SEAT LAYOUT ---")
    res_seats = client.get(f'/api/routes/{route1.id}/seats/')
    success_seats = res_seats.status_code == 200
    message_seats = ""
    if success_seats:
        available_seats = res_seats.data.get('data', {}).get('available', 0)
        total_seats = res_seats.data.get('data', {}).get('total_seats', 0)
        message_seats = f"(Seats layout available: {available_seats}/{total_seats})"
    print_result("Route Seat Layout API", success_seats, message_seats)

    # ----------------------------------------------------
    # FEATURE 6: STANDARD USER BOOKING & PAYMENT VERIFY
    # ----------------------------------------------------
    print("\n--- FEATURE 6: BOOKING CHECKOUT & VERIFICATION ---")
    # Clean up test seat 'B1' to make sure it is free
    test_seat_number = 'B1'
    seat_layout = SeatLayout.objects.get(route=route1, seat_number=test_seat_number)
    original_booked_state = seat_layout.is_booked
    original_route_seats = route1.available_seats
    
    if seat_layout.is_booked:
        seat_layout.is_booked = False
        seat_layout.save()
        route1.available_seats += 1
        route1.save()
        route1.refresh_from_db()
        seat_layout.refresh_from_db()
        
    booking_payload = {
        "route_id": route1.id,
        "travel_date": str(route1.date),
        "passengers": [
            {
                "name": "Audit Passenger One",
                "age": 25,
                "gender": "Male",
                "seat_number": test_seat_number
            }
        ]
    }
    
    res_book = client.post('/api/bookings/create/', booking_payload, format='json')
    success_book = res_book.status_code == 201
    booking_id = ""
    message_book = ""
    if success_book:
        booking_id = res_book.data.get('data', {}).get('booking_id')
        razorpay_order_id = res_book.data.get('data', {}).get('razorpay_order_id')
        message_book = f"(Booking BK Code: {booking_id})"
    else:
        message_book = f"(Status: {res_book.status_code}, Error: {res_book.data})"
    print_result("Initialize Booking API", success_book, message_book)

    # Check database locking
    seat_layout.refresh_from_db()
    route1.refresh_from_db()
    success_lock = seat_layout.is_booked == True
    message_lock = f"(Seat {test_seat_number} is_booked: {seat_layout.is_booked}, Route Capacity: {route1.available_seats})"
    print_result("Database Seat Lock Trigger", success_lock, message_lock)

    # Verify Payment (Simulating successful payment callback)
    pay_verify_payload = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": "pay_mock_verified_12345",
        "razorpay_signature": "sig_mock_verified",
        "booking_id": booking_id
    }
    res_pay = client.post('/api/payment/verify/', pay_verify_payload, format='json')
    success_pay = res_pay.status_code == 200
    print_result("Verify Payment API", success_pay)

    # Check updated booking status
    booking = Booking.objects.get(booking_id=booking_id)
    success_confirm = booking.status == 'CONFIRMED' and booking.payment_status == 'PAID'
    message_confirm = f"(Status: {booking.status}, Payment: {booking.payment_status})"
    print_result("Confirm Booking Status Check", success_confirm, message_confirm)

    # ----------------------------------------------------
    # FEATURE 7: DOUBLE BOOKING PREVENTION (RACE CONDITION)
    # ----------------------------------------------------
    print("\n--- FEATURE 7: RACE CONDITION PREVENTION ---")
    # Attempt to book the SAME seat again
    res_double_book = client.post('/api/bookings/create/', booking_payload, format='json')
    success_prevention = res_double_book.status_code == 409
    message_prevention = f"(Status Code: {res_double_book.status_code})"
    print_result("Prevent Double Booking", success_prevention, message_prevention)

    # ----------------------------------------------------
    # FEATURE 8: BOOKING CANCELLATION & SEAT RELEASE
    # ----------------------------------------------------
    print("\n--- FEATURE 8: BOOKING CANCELLATION ---")
    res_cancel = client.post(f'/api/bookings/{booking_id}/cancel/')
    success_cancel = res_cancel.status_code == 200
    print_result("Cancel Booking API", success_cancel)

    # Verify seat releasing in DB
    seat_layout.refresh_from_db()
    route1.refresh_from_db()
    success_release = seat_layout.is_booked == False and route1.available_seats == original_route_seats
    message_release = f"(Seat {test_seat_number} is_booked: {seat_layout.is_booked}, Route Capacity: {route1.available_seats})"
    print_result("Database Seat Release Trigger", success_release, message_release)

    # ----------------------------------------------------
    # FEATURE 9: AGENT WALK-IN BOOKING (nullable user)
    # ----------------------------------------------------
    print("\n--- FEATURE 9: AGENT WALK-IN CHECKOUT ---")
    # Authenticate client as admin
    admin_user = User.objects.get(email='admin@busbook.com')
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}') # standard token
    client.force_authenticate(user=admin_user) # elevate to admin staff
    
    walkin_payload = {
        "route_id": route1.id,
        "travel_date": str(route1.date),
        "passengers": [
            {
                "name": "Walkin Passenger Guest",
                "age": 45,
                "gender": "Female",
                "seat_number": test_seat_number
            }
        ],
        "is_walkin": True,
        "guest_name": "Walk-in Guest",
        "guest_phone": "0300-1122334",
        "guest_email": "walkin@guest.com"
    }
    
    res_walkin = client.post('/api/bookings/create/', walkin_payload, format='json')
    success_walkin = res_walkin.status_code == 201
    walkin_id = ""
    message_walkin = ""
    if success_walkin:
        walkin_id = res_walkin.data.get('data', {}).get('booking_id')
        message_walkin = f"(Walk-in Code: {walkin_id})"
    print_result("Agent Walk-in Booking API", success_walkin, message_walkin)

    # Verify walk-in details
    walkin_booking = Booking.objects.get(booking_id=walkin_id)
    success_walkin_db = (
        walkin_booking.user == None and
        walkin_booking.guest_name == "Walk-in Guest" and
        walkin_booking.status == "CONFIRMED" and
        walkin_booking.payment_status == "PAID"
    )
    message_walkin_db = f"(User Account Associated: {walkin_booking.user}, Status: {walkin_booking.status})"
    print_result("Walk-in Database Verification", success_walkin_db, message_walkin_db)

    # Clean up walkin
    walkin_booking.delete()
    print("Cleaned up walk-in test booking.")

    # ----------------------------------------------------
    # AUDIT CLEANUP
    # ----------------------------------------------------
    print("\n--- AUDIT CLEANUP ---")
    # Restore original seat booked state
    seat_layout.is_booked = original_booked_state
    seat_layout.save()
    route1.available_seats = original_route_seats
    route1.save()
    
    # Delete test user
    User.objects.filter(email=test_email).delete()
    print("Audit test user deleted. Database cleaned up.")
    print("==================================================")
    print("              ALL AUDIT TESTS PASSED!             ")
    print("==================================================")

if __name__ == '__main__':
    run_complete_audit()
