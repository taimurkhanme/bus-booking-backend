import random
import string
from django.db import transaction
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from ..models import Route, Booking, Passenger, SeatLayout, Payment
from ..serializers import BookingListSerializer, BookingDetailSerializer
from ..permissions import IsOwnerOrAdmin
import razorpay

class BookingCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        route_id = request.data.get('route_id')
        travel_date = request.data.get('travel_date')
        passengers_data = request.data.get('passengers', [])

        if not route_id or not travel_date or not passengers_data:
            return Response({
                'success': False,
                'error': 'Parameters route_id, travel_date and passengers list are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. Lock the route using select_for_update
                route = Route.objects.select_for_update().get(id=route_id)
                
                # Check route travel date match
                if str(route.date) != str(travel_date):
                    return Response({
                        'success': False,
                        'error': f"Route ID {route_id} does not schedule for date {travel_date}."
                    }, status=status.HTTP_400_BAD_REQUEST)

                seat_numbers = [p['seat_number'] for p in passengers_data]
                
                # 2. Lock and fetch SeatLayouts to verify availability
                seats = SeatLayout.objects.select_for_update().filter(
                    route=route, 
                    seat_number__in=seat_numbers
                )

                if len(seats) != len(seat_numbers):
                    return Response({
                        'success': False,
                        'error': 'Some requested seats do not exist in this bus route layout.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                for seat in seats:
                    if seat.is_booked:
                        return Response({
                            'success': False,
                            'error': f"Seat {seat.seat_number} is already booked. Please choose another seat."
                        }, status=status.HTTP_409_CONFLICT)

                # 3. Calculate total amount
                total_amount = route.price * len(passengers_data)

                # 4. Create Booking
                user = request.user
                status_val = 'PENDING'
                payment_status_val = 'PENDING'
                guest_name = None
                guest_phone = None
                guest_email = None

                is_walkin = request.data.get('is_walkin', False)
                if is_walkin and request.user.is_staff:
                    user = None
                    status_val = 'CONFIRMED'
                    payment_status_val = 'PAID'
                    guest_name = request.data.get('guest_name')
                    guest_phone = request.data.get('guest_phone')
                    guest_email = request.data.get('guest_email')

                booking = Booking.objects.create(
                    user=user,
                    guest_name=guest_name,
                    guest_phone=guest_phone,
                    guest_email=guest_email,
                    route=route,
                    total_amount=total_amount,
                    status=status_val,
                    payment_status=payment_status_val,
                    travel_date=travel_date
                )

                # 5. Save Passengers and Mark seats as booked
                for p_data in passengers_data:
                    Passenger.objects.create(
                        booking=booking,
                        name=p_data['name'],
                        age=int(p_data['age']),
                        gender=p_data['gender'],
                        seat_number=p_data['seat_number']
                    )
                    
                    # Mark seat as booked
                    seat = seats.get(seat_number=p_data['seat_number'])
                    seat.is_booked = True
                    seat.save()

                # 6. Update Route's available seats
                route.available_seats -= len(passengers_data)
                route.save()

                # 7. Initialize Payment / Create Razorpay Order
                # Setup a mock/temporary order ID by default
                order_id = "order_" + "".join(random.choices(string.ascii_letters + string.digits, k=14))
                payment_status_log = 'CREATED'

                if is_walkin and request.user.is_staff:
                    order_id = "walkin_" + "".join(random.choices(string.ascii_letters + string.digits, k=10))
                    payment_status_log = 'PAID'
                else:
                    # Try initializing with Razorpay client if keys are not defaults
                    if settings.RAZORPAY_KEY_ID != 'your-razorpay-key' and settings.RAZORPAY_KEY_SECRET != 'your-razorpay-secret':
                        try:
                            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                            amount_in_paise = int(total_amount * 100) # Convert PKR to Paise
                            
                            razorpay_order = client.order.create({
                                'amount': amount_in_paise,
                                'currency': 'PKR',
                                'receipt': booking.booking_id,
                                'payment_capture': 1
                            })
                            order_id = razorpay_order['id']
                        except Exception as e:
                            # Log error, fallback to mock order ID to make sure testing doesn't break
                            print("Razorpay API Exception:", e)

                # Save payment tracking record
                Payment.objects.create(
                    booking=booking,
                    razorpay_order_id=order_id,
                    amount=total_amount,
                    status=payment_status_log
                )

                return Response({
                    'success': True,
                    'data': {
                        'booking_id': booking.booking_id,
                        'total_amount': float(total_amount),
                        'razorpay_order_id': order_id
                    },
                    'message': 'Booking initialized successfully.'
                }, status=status.HTTP_201_CREATED)

        except Route.DoesNotExist:
            return Response({
                'success': False,
                'error': f"Route with ID {route_id} does not exist."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BookingListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        print(f"\n--- GET BOOKINGS REQUEST ---")
        print(f"Requesting user: email='{request.user.email}', is_staff={request.user.is_staff}")
        
        # Log all bookings in DB for comparison
        all_bookings = Booking.objects.all()
        print(f"Total bookings in DB: {all_bookings.count()}")
        for b in all_bookings:
            user_email = b.user.email if b.user else f"Guest ({b.guest_name})"
            print(f" - Booking ID {b.booking_id}: status={b.status}, payment_status={b.payment_status}, user={user_email}, travel_date={b.travel_date}")

        # Users see their own bookings; admins see everything
        if request.user.is_staff:
            bookings = Booking.objects.all()
            print(f"Staff user: showing all {bookings.count()} bookings.")
        else:
            bookings = Booking.objects.filter(user=request.user)
            print(f"Regular user: showing {bookings.count()} bookings for user '{request.user.email}'.")
        print(f"----------------------------\n")
            
        serializer = BookingListSerializer(bookings, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class BookingDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get(self, request, booking_id):
        booking = get_object_or_404(Booking, booking_id=booking_id)
        self.check_object_permissions(request, booking)
        
        serializer = BookingDetailSerializer(booking)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def patch(self, request, booking_id):
        booking = get_object_or_404(Booking, booking_id=booking_id)
        self.check_object_permissions(request, booking)
        
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Permission denied. Staff access required.'
            }, status=status.HTTP_403_FORBIDDEN)
            
        status_val = request.data.get('status')
        payment_status_val = request.data.get('payment_status')
        
        updated = False
        if status_val is not None:
            if status_val not in dict(Booking.STATUS_CHOICES):
                return Response({
                    'success': False,
                    'error': f"Invalid status: {status_val}. Valid options are PENDING, CONFIRMED, CANCELLED."
                }, status=status.HTTP_400_BAD_REQUEST)
            booking.status = status_val
            updated = True
            
        if payment_status_val is not None:
            if payment_status_val not in dict(Booking.PAYMENT_STATUS_CHOICES):
                return Response({
                    'success': False,
                    'error': f"Invalid payment_status: {payment_status_val}. Valid options are PENDING, PAID, FAILED, REFUNDED."
                }, status=status.HTTP_400_BAD_REQUEST)
            booking.payment_status = payment_status_val
            updated = True
            
        if updated:
            try:
                with transaction.atomic():
                    booking.save()
            except Exception as e:
                return Response({
                    'success': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        serializer = BookingDetailSerializer(booking)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class BookingCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, booking_id=booking_id)
        self.check_object_permissions(request, booking)

        if booking.status == 'CANCELLED':
            return Response({
                'success': False,
                'error': 'This booking is already cancelled.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. Update Booking status
                booking.status = 'CANCELLED'
                
                # Refund payments if status was PAID
                if booking.payment_status == 'PAID':
                    booking.payment_status = 'REFUNDED'
                    # Also update payment log status
                    payment = booking.payments.filter(status='PAID').first()
                    if payment:
                        payment.status = 'FAILED'  # Cancelled/reversed
                        payment.save()
                else:
                    booking.payment_status = 'FAILED'
                
                # Saving booking will trigger seat release and capacity restore in the model
                booking.save()

                return Response({
                    'success': True,
                    'message': 'Booking cancelled successfully. Seats have been released.'
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
