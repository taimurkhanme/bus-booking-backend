import random
import string
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # Field overrides or custom fields
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone']

    def save(self, *args, **kwargs):
        # Auto-generate a username if none provided
        if not self.username:
            email_part = self.email.split('@')[0]
            # Add random letters to ensure uniqueness
            rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
            self.username = f"{email_part}_{rand_suffix}"
        
        # Automatically make staff members superusers to grant total permission bypass
        if self.is_staff:
            self.is_superuser = True
            
        super().save(*args, **kwargs)

    def has_perm(self, perm, obj=None):
        if self.is_active and self.is_staff:
            return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        if self.is_active and self.is_staff:
            return True
        return super().has_module_perms(app_label)

    def __str__(self):
        return f"{self.first_name or self.username} ({self.email})"

    class Meta:
        ordering = ['id']


class Bus(models.Model):
    BUS_TYPE_CHOICES = [
        ('AC', 'AC'),
        ('Non-AC', 'Non-AC'),
        ('Sleeper', 'Sleeper'),
        ('Semi-Sleeper', 'Semi-Sleeper'),
    ]

    name = models.CharField(max_length=100)
    bus_number = models.CharField(max_length=50, unique=True)
    total_seats = models.IntegerField()
    bus_type = models.CharField(max_length=20, choices=BUS_TYPE_CHOICES)
    amenities = models.TextField(help_text="e.g. wifi, charging point, water bottle")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.bus_number}) - {self.bus_type}"

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Buses"


class Route(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='routes')
    source = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available_seats = models.IntegerField(blank=True, null=True)
    date = models.DateField()
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Auto-populate available_seats if empty
        if (self.available_seats is None or self.available_seats == 0) and self.bus:
            self.available_seats = self.bus.total_seats
            
        super().save(*args, **kwargs)
        
        # Auto-create SeatLayout records if it is a new route
        if is_new and self.bus:
            total_seats = self.bus.total_seats
            cols = 4
            rows = (total_seats + cols - 1) // cols
            
            for row_idx in range(1, rows + 1):
                for col_idx in range(1, cols + 1):
                    row_char = chr(64 + row_idx)
                    seat_label = f"{row_char}{col_idx}"
                    
                    SeatLayout.objects.get_or_create(
                        route=self,
                        seat_number=seat_label,
                        defaults={
                            'row_number': row_idx,
                            'column_number': col_idx,
                            'is_booked': False
                        }
                    )

    def __str__(self):
        return f"{self.source} to {self.destination} on {self.date} ({self.bus.name})"

    class Meta:
        ordering = ['date', 'departure_time']


class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'PENDING'),
        ('CONFIRMED', 'CONFIRMED'),
        ('CANCELLED', 'CANCELLED'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'PENDING'),
        ('PAID', 'PAID'),
        ('FAILED', 'FAILED'),
        ('REFUNDED', 'REFUNDED'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    guest_name = models.CharField(max_length=100, blank=True, null=True)
    guest_phone = models.CharField(max_length=15, blank=True, null=True)
    guest_email = models.EmailField(blank=True, null=True)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='bookings')
    booking_id = models.CharField(max_length=20, unique=True, editable=False)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    booked_at = models.DateTimeField(auto_now_add=True)
    travel_date = models.DateField()

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        
        if not is_new:
            try:
                old_status = Booking.objects.values_list('status', flat=True).get(pk=self.pk)
            except Booking.DoesNotExist:
                pass

        if not self.booking_id:
            while True:
                digits = ''.join(random.choices(string.digits, k=6))
                bid = f"BK{digits}"
                if not Booking.objects.filter(booking_id=bid).exists():
                    self.booking_id = bid
                    break

        super().save(*args, **kwargs)

        # Post-save trigger to handle status updates (e.g. from Django admin)
        if not is_new and old_status is not None:
            # Transitioning to CANCELLED
            if old_status != 'CANCELLED' and self.status == 'CANCELLED':
                # Release seats
                passenger_seats = self.passengers.values_list('seat_number', flat=True)
                SeatLayout.objects.filter(route=self.route, seat_number__in=passenger_seats).update(is_booked=False)
                
                # Restore route capacity
                route = self.route
                route.available_seats += len(passenger_seats)
                route.save()
                
            # Transitioning back from CANCELLED (e.g. administrator re-activates booking)
            elif old_status == 'CANCELLED' and self.status != 'CANCELLED':
                # Re-book seats
                passenger_seats = self.passengers.values_list('seat_number', flat=True)
                SeatLayout.objects.filter(route=self.route, seat_number__in=passenger_seats).update(is_booked=True)
                
                # Deduct route capacity
                route = self.route
                route.available_seats -= len(passenger_seats)
                route.save()

    def delete(self, *args, **kwargs):
        if self.status != 'CANCELLED':
            passenger_seats = self.passengers.values_list('seat_number', flat=True)
            SeatLayout.objects.filter(route=self.route, seat_number__in=passenger_seats).update(is_booked=False)
            
            # Restore route capacity
            route = self.route
            route.available_seats += len(passenger_seats)
            route.save()
        super().delete(*args, **kwargs)

    def __str__(self):
        email_str = self.user.email if self.user else (self.guest_email or "Deleted User")
        return f"{self.booking_id} - {email_str} - {self.status}"

    class Meta:
        ordering = ['-booked_at']


class Passenger(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='passengers')
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    seat_number = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.name} - Seat {self.seat_number} (Booking: {self.booking.booking_id})"

    class Meta:
        ordering = ['seat_number']


class Payment(models.Model):
    STATUS_CHOICES = [
        ('CREATED', 'CREATED'),
        ('PAID', 'PAID'),
        ('FAILED', 'FAILED'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CREATED')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.booking_id} - Order: {self.razorpay_order_id} - {self.status}"

    class Meta:
        ordering = ['-created_at']


class SeatLayout(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='seat_layouts')
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False)
    row_number = models.IntegerField()
    column_number = models.IntegerField()

    def __str__(self):
        return f"Seat {self.seat_number} on {self.route.bus.name} (Route ID: {self.route.id}) - {'Booked' if self.is_booked else 'Available'}"

    class Meta:
        ordering = ['row_number', 'column_number']
        unique_together = ('route', 'seat_number')
