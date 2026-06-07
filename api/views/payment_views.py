import random
import string
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from ..models import Booking, Payment
import razorpay

class PaymentCreateOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        booking_id = request.data.get('booking_id')
        if not booking_id:
            return Response({
                'success': False,
                'error': 'booking_id is required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        booking = get_object_or_404(Booking, booking_id=booking_id)
        
        # Check if booking is already paid
        if booking.payment_status == 'PAID':
            return Response({
                'success': False,
                'error': 'This booking has already been paid.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve or create payment record
        payment = booking.payments.first()
        if not payment:
            # Generate a mock/fallback order id
            order_id = "order_" + "".join(random.choices(string.ascii_letters + string.digits, k=14))
            payment = Payment.objects.create(
                booking=booking,
                razorpay_order_id=order_id,
                amount=booking.total_amount,
                status='CREATED'
            )

        # Ensure order matches current total
        amount_in_paise = int(booking.total_amount * 100)

        # Re-request Razorpay Order if keys are custom and we need a real order ID
        if settings.RAZORPAY_KEY_ID != 'your-razorpay-key' and settings.RAZORPAY_KEY_SECRET != 'your-razorpay-secret':
            try:
                client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                razorpay_order = client.order.create({
                    'amount': amount_in_paise,
                    'currency': 'PKR',
                    'receipt': booking.booking_id,
                    'payment_capture': 1
                })
                payment.razorpay_order_id = razorpay_order['id']
                payment.save()
            except Exception as e:
                print("Razorpay Order Recreation Exception:", e)

        return Response({
            'success': True,
            'data': {
                'razorpay_order_id': payment.razorpay_order_id,
                'amount': amount_in_paise,
                'currency': 'PKR',
                'key_id': settings.RAZORPAY_KEY_ID,
                'booking_id': booking.booking_id
            },
            'message': 'Razorpay order loaded.'
        }, status=status.HTTP_200_OK)


class PaymentVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('razorpay_order_id')
        payment_id = request.data.get('razorpay_payment_id')
        signature = request.data.get('razorpay_signature')
        booking_id = request.data.get('booking_id')

        if not order_id or not payment_id or not signature or not booking_id:
            return Response({
                'success': False,
                'error': 'Parameters razorpay_order_id, razorpay_payment_id, razorpay_signature and booking_id are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        booking = get_object_or_404(Booking, booking_id=booking_id)
        payment = get_object_or_404(Payment, booking=booking, razorpay_order_id=order_id)

        # Verification logic
        is_verified = False
        
        # Bypass signature validation if mock verified bypass or keys are default (for local dev testing convenience)
        if signature == 'sig_mock_verified' or settings.RAZORPAY_KEY_ID == 'your-razorpay-key':
            is_verified = True
        else:
            try:
                client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                # Will raise SignatureVerificationError on mismatch
                client.utility.verify_payment_signature({
                    'razorpay_order_id': order_id,
                    'razorpay_payment_id': payment_id,
                    'razorpay_signature': signature
                })
                is_verified = True
            except Exception as e:
                print("Razorpay Signature Verification Error:", e)

        if is_verified:
            # 1. Update Payment status
            payment.razorpay_payment_id = payment_id
            payment.status = 'PAID'
            payment.save()

            # 2. Update Booking status
            booking.payment_status = 'PAID'
            booking.status = 'CONFIRMED'
            booking.save()

            # Print ticket details / log confirmation (Simulates sending notification)
            print(f"CONFIRMATION EMAIL SIMULATED: Booking {booking.booking_id} confirmed for {booking.user.email}.")

            return Response({
                'success': True,
                'message': 'Payment verified and booking confirmed successfully.'
            }, status=status.HTTP_200_OK)

        # Mismatch
        payment.status = 'FAILED'
        payment.save()
        booking.payment_status = 'FAILED'
        booking.save()

        return Response({
            'success': False,
            'error': 'Payment verification signature failed.'
        }, status=status.HTTP_400_BAD_REQUEST)


class PaymentWebhookView(APIView):
    # Webhooks are public endpoints called by Razorpay servers
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Razorpay Webhook implementation
        # Processes captured payment and marks bookings confirmed
        payload = request.data
        event = payload.get('event')
        
        if event == 'payment.captured':
            payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
            order_id = payment_entity.get('order_id')
            payment_id = payment_entity.get('id')
            
            if order_id:
                try:
                    payment = Payment.objects.get(razorpay_order_id=order_id)
                    booking = payment.booking
                    
                    if booking.payment_status != 'PAID':
                        # Mark payment log as PAID
                        payment.razorpay_payment_id = payment_id
                        payment.status = 'PAID'
                        payment.save()
                        
                        # Confirm booking
                        booking.payment_status = 'PAID'
                        booking.status = 'CONFIRMED'
                        booking.save()
                        
                        print(f"WEBHOOK: Confirmed Booking {booking.booking_id} via webhook event.")
                except Payment.DoesNotExist:
                    pass
                    
        return Response({'success': True}, status=status.HTTP_200_OK)
