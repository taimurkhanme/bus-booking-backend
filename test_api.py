import os
import django

# Initialize Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bus_booking.settings")
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from api.models import Booking

def run_api_tests():
    from django.conf import settings
    if 'testserver' not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append('testserver')

    print("==================================================")
    print("                API DIAGNOSTIC TEST               ")
    print("==================================================")

    # 1. Get the regular user
    User = get_user_model()
    try:
        user = User.objects.get(email='professorguideline@gmail.com')
        print(f"Testing with user: {user.email}")
    except User.DoesNotExist:
        print("User professorguideline@gmail.com not found!")
        return

    # 2. Setup API Client and authenticate
    client = APIClient()
    client.force_authenticate(user=user)

    # 3. Retrieve Bookings via API
    print("\n[Step 1] Querying GET /api/bookings/ (API Call):")
    res1 = client.get('/api/bookings/')
    print(f"Response Status Code: {res1.status_code}")
    print(f"Response Data Payload:")
    for booking_data in res1.data.get('data', []):
        print(f" - Booking {booking_data['booking_id']}: status='{booking_data['status']}'")

    # 4. Modify a booking in DB (simulating admin change in Django admin)
    booking_id = 'BK051774'
    try:
        booking = Booking.objects.get(booking_id=booking_id)
        original_status = booking.status
        new_status = 'CONFIRMED' if original_status == 'PENDING' else 'PENDING'
        
        print(f"\n[Step 2] Modifying Booking {booking_id} status in DB: '{original_status}' -> '{new_status}'")
        booking.status = new_status
        booking.save()
        
        # 5. Query the API again to check if it returns the updated status
        print("\n[Step 3] Re-querying GET /api/bookings/ (API Call):")
        res2 = client.get('/api/bookings/')
        print(f"Response Status Code: {res2.status_code}")
        print(f"Response Data Payload:")
        found_updated = False
        for booking_data in res2.data.get('data', []):
            print(f" - Booking {booking_data['booking_id']}: status='{booking_data['status']}'")
            if booking_data['booking_id'] == booking_id and booking_data['status'] == new_status:
                found_updated = True
                
        # 6. Verify single booking details API
        print(f"\n[Step 4] Querying GET /api/bookings/{booking_id}/ (API Call):")
        res3 = client.get(f'/api/bookings/{booking_id}/')
        print(f"Response Status Code: {res3.status_code}")
        api_booking_status = res3.data.get('data', {}).get('status')
        print(f"Single Booking status returned: '{api_booking_status}'")

        if found_updated and api_booking_status == new_status:
            print("\nSUCCESS: The Django API correctly returns the updated database status!")
        else:
            print("\nFAILURE: The Django API did NOT return the updated status!")

        # Restore original status
        booking.status = original_status
        booking.save()
        print(f"\nRestored Booking {booking_id} status back to '{original_status}'.")

    except Booking.DoesNotExist:
        print(f"Booking {booking_id} not found in DB. Cannot test updates.")

if __name__ == '__main__':
    run_api_tests()
