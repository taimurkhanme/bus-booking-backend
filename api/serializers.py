import random
import string
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Bus, Route, Booking, Passenger, Payment, SeatLayout

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='first_name', required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'first_name', 'email', 'phone', 'profile_picture', 'is_staff']


class UserRegistrationSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=6)

    class Meta:
        model = User
        fields = ['name', 'email', 'phone', 'password']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        name = validated_data.pop('name')
        password = validated_data.pop('password')
        email = validated_data['email']
        
        # Pass a unique username constructed from the email prefix
        email_prefix = email.split('@')[0]
        rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        username = f"{email_prefix}_{rand_suffix}"
        
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=name,
            phone=validated_data['phone'],
            password=password
        )
        return user


class BusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bus
        fields = '__all__'


class RouteSerializer(serializers.ModelSerializer):
    bus = BusSerializer(read_only=True)
    bus_id = serializers.PrimaryKeyRelatedField(
        queryset=Bus.objects.all(),
        source='bus',
        write_only=True
    )

    class Meta:
        model = Route
        fields = ['id', 'bus', 'bus_id', 'source', 'destination', 'departure_time', 'arrival_time', 'price', 'available_seats', 'date', 'is_active']


class SeatLayoutSerializer(serializers.ModelSerializer):
    # Map row_number/column_number to row/col for frontend compatibility
    row = serializers.IntegerField(source='row_number')
    col = serializers.IntegerField(source='column_number')

    class Meta:
        model = SeatLayout
        fields = ['seat_number', 'row', 'col', 'row_number', 'column_number', 'is_booked']


class PassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = ['name', 'age', 'gender', 'seat_number']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['amount', 'status', 'razorpay_order_id']


class BookingListSerializer(serializers.ModelSerializer):
    route = RouteSerializer(read_only=True)
    passengers_count = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ['booking_id', 'route', 'status', 'travel_date', 'total_amount', 'booked_at', 'passengers_count', 'guest_name', 'guest_phone', 'guest_email']

    def get_passengers_count(self, obj):
        return obj.passengers.count()


class BookingDetailSerializer(serializers.ModelSerializer):
    route = RouteSerializer(read_only=True)
    passengers = PassengerSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = ['booking_id', 'route', 'status', 'payment_status', 'travel_date', 'total_amount', 'booked_at', 'passengers', 'payments', 'guest_name', 'guest_phone', 'guest_email']
