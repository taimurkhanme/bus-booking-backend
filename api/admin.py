from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Bus, Route, Booking, Passenger, Payment, SeatLayout

class PassengerInline(admin.TabularInline):
    model = Passenger
    extra = 0
    fields = ('name', 'age', 'gender', 'seat_number')


class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'phone', 'staff_badge', 'active_badge')
    search_fields = ('email', 'first_name', 'phone')
    ordering = ('id',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Profile Info', {'fields': ('phone', 'profile_picture')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Profile Info', {'fields': ('phone', 'profile_picture')}),
    )
    
    def full_name(self, obj):
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip() or obj.username
    full_name.short_description = 'Name'
    
    def staff_badge(self, obj):
        if obj.is_staff:
            return format_html('<span style="background-color:#ede9fe; color:#5b21b6; padding:2px 8px; border-radius:9999px; font-size:10px; font-weight:700;">STAFF</span>')
        return format_html('<span style="color:#94a3b8; font-size:10px;">Customer</span>')
    staff_badge.short_description = 'Role'
    staff_badge.admin_order_field = 'is_staff'
    
    def active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#047857; font-weight:700;">Active</span>')
        return format_html('<span style="color:#b91c1c; font-weight:700;">Deactivated</span>')
    active_badge.short_description = 'Status'
    active_badge.admin_order_field = 'is_active'


class BusAdmin(admin.ModelAdmin):
    list_display = ('name', 'bus_number', 'bus_type', 'seats_info', 'colored_active')
    search_fields = ('name', 'bus_number')
    list_filter = ('bus_type', 'is_active')
    
    def seats_info(self, obj):
        return format_html(
            '<strong>{}</strong> <span style="color:#64748b; font-size:11px;">seats</span>',
            obj.total_seats
        )
    seats_info.short_description = 'Capacity'
    seats_info.admin_order_field = 'total_seats'
    
    def colored_active(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#047857; font-weight:700;">Active</span>')
        return format_html('<span style="color:#b91c1c; font-weight:700;">Suspended</span>')
    colored_active.short_description = 'Status'
    colored_active.admin_order_field = 'is_active'


class RouteAdmin(admin.ModelAdmin):
    list_display = ('formatted_route', 'bus_info', 'departure_info', 'fare_info', 'seats_info', 'colored_active')
    search_fields = ('source', 'destination', 'bus__name')
    list_filter = ('date', 'source', 'destination', 'is_active')
    
    def formatted_route(self, obj):
        return format_html('<strong>{} &rarr; {}</strong>', obj.source, obj.destination)
    formatted_route.short_description = 'Route'
    
    def bus_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><span style="color:#64748b; font-size:11px;">{} • {}</span>',
            obj.bus.name,
            obj.bus.bus_number,
            obj.bus.bus_type
        )
    bus_info.short_description = 'Bus Operator'
    
    def departure_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><span style="color:#64748b; font-size:11px;">Dep: {}</span>',
            obj.date.strftime('%b %d, %Y'),
            obj.departure_time.strftime('%I:%M %p')
        )
    departure_info.short_description = 'Date & Departure'
    departure_info.admin_order_field = 'date'
    
    def fare_info(self, obj):
        formatted_price = f"PKR {obj.price:,.2f}"
        return format_html('<strong>{}</strong>', formatted_price)
    fare_info.short_description = 'Fare'
    fare_info.admin_order_field = 'price'
    
    def seats_info(self, obj):
        percent = int(((obj.available_seats or 0) / obj.bus.total_seats) * 100) if obj.bus and obj.bus.total_seats else 0
        color = '#047857' if percent > 30 else '#b45309'
        return format_html(
            '<strong style="color:{};">{}/{}</strong><br><span style="color:#64748b; font-size:10px;">{}% Available</span>',
            color,
            obj.available_seats,
            obj.bus.total_seats,
            percent
        )
    seats_info.short_description = 'Available'
    seats_info.admin_order_field = 'available_seats'
    
    def colored_active(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#047857; font-weight:700;">Active</span>')
        return format_html('<span style="color:#b91c1c; font-weight:700;">Cancelled</span>')
    colored_active.short_description = 'Status'
    colored_active.admin_order_field = 'is_active'


class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'booking_id',
        'customer_contact',
        'formatted_route',
        'fare_details',
        'colored_status',
        'colored_payment_status',
        'booked_at'
    )
    search_fields = ('booking_id', 'user__email', 'guest_name', 'guest_phone', 'route__source', 'route__destination')
    list_filter = ('status', 'payment_status', 'travel_date')
    inlines = [PassengerInline]
    actions = ['confirm_bookings', 'cancel_bookings']

    def confirm_bookings(self, request, queryset):
        count = 0
        for booking in queryset:
            if booking.status != 'CONFIRMED':
                booking.status = 'CONFIRMED'
                booking.payment_status = 'PAID'
                booking.save()
                count += 1
        self.message_user(request, f"{count} booking(s) successfully confirmed & marked as paid.")
    confirm_bookings.short_description = "✔ Confirm selected bookings & mark PAID"

    def cancel_bookings(self, request, queryset):
        count = 0
        for booking in queryset:
            if booking.status != 'CANCELLED':
                booking.status = 'CANCELLED'
                booking.payment_status = 'REFUNDED'
                booking.save()
                count += 1
        self.message_user(request, f"{count} booking(s) successfully cancelled & refunded.")
    cancel_bookings.short_description = "❌ Cancel selected bookings & mark REFUNDED"
    
    def customer_contact(self, obj):
        if obj.user:
            return format_html(
                '<strong>{}</strong><br><span style="color:#64748b; font-size:11px;">{}</span>',
                obj.user.first_name or obj.user.username,
                obj.user.email
            )
        else:
            return format_html(
                '<strong>{}</strong> <span style="background-color:#ede9fe; color:#6d28d9; padding:2px 6px; border-radius:4px; font-size:10px; font-weight:700;">GUEST</span><br><span style="color:#64748b; font-size:11px;">{}</span>',
                obj.guest_name or "Anonymous",
                obj.guest_phone or ""
            )
    customer_contact.short_description = 'Customer'
    
    def formatted_route(self, obj):
        return format_html(
            '<strong style="color:#0f172a;">{} &rarr; {}</strong><br><span style="color:#6366f1; font-size:11px; font-weight:600;">{}</span>',
            obj.route.source,
            obj.route.destination,
            obj.travel_date.strftime('%b %d, %Y')
        )
    formatted_route.short_description = 'Route / Date'
    formatted_route.admin_order_field = 'route'
    
    def fare_details(self, obj):
        count = obj.passengers.count()
        formatted_amount = f"PKR {obj.total_amount:,.2f}"
        return format_html(
            '<strong style="color:#1e293b;">{}</strong><br><span style="color:#64748b; font-size:11px;">{} seat(s)</span>',
            formatted_amount,
            count
        )
    fare_details.short_description = 'Fare Details'
    
    def colored_status(self, obj):
        colors = {
            'PENDING': 'background-color: #fffbeb; color: #b45309; border: 1px solid #fde68a;',
            'CONFIRMED': 'background-color: #ecfdf5; color: #047857; border: 1px solid #a7f3d0;',
            'CANCELLED': 'background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca;',
        }
        style = colors.get(obj.status, 'background-color: #f3f4f6; color: #374151;')
        return format_html(
            '<span style="padding: 4px 12px; border-radius: 9999px; font-size: 11px; font-weight: 700; text-transform: uppercase; {}">{}</span>',
            style,
            obj.status
        )
    colored_status.short_description = 'Booking Status'
    colored_status.admin_order_field = 'status'

    def colored_payment_status(self, obj):
        colors = {
            'PENDING': 'background-color: #fffbeb; color: #b45309; border: 1px solid #fde68a;',
            'PAID': 'background-color: #ecfdf5; color: #047857; border: 1px solid #a7f3d0;',
            'FAILED': 'background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca;',
            'REFUNDED': 'background-color: #f0f9ff; color: #0369a1; border: 1px solid #bae6fd;',
        }
        style = colors.get(obj.payment_status, 'background-color: #f3f4f6; color: #374151;')
        return format_html(
            '<span style="padding: 4px 12px; border-radius: 9999px; font-size: 11px; font-weight: 700; text-transform: uppercase; {}">{}</span>',
            style,
            obj.payment_status
        )
    colored_payment_status.short_description = 'Payment Status'
    colored_payment_status.admin_order_field = 'payment_status'


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking_link', 'formatted_amount', 'currency', 'colored_status', 'razorpay_order_id', 'created_at')
    search_fields = ('booking__booking_id', 'razorpay_order_id', 'razorpay_payment_id')
    list_filter = ('status', 'currency', 'created_at')
    
    def booking_link(self, obj):
        return format_html('<strong style="color:#2563eb;">{}</strong>', obj.booking.booking_id)
    booking_link.short_description = 'Booking ID'
    booking_link.admin_order_field = 'booking__booking_id'
    
    def formatted_amount(self, obj):
        formatted_price = f"PKR {obj.amount:,.2f}"
        return format_html('<strong>{}</strong>', formatted_price)
    formatted_amount.short_description = 'Amount'
    formatted_amount.admin_order_field = 'amount'
    
    def colored_status(self, obj):
        colors = {
            'CREATED': 'background-color: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb;',
            'PAID': 'background-color: #ecfdf5; color: #047857; border: 1px solid #a7f3d0;',
            'FAILED': 'background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca;',
        }
        style = colors.get(obj.status, 'background-color: #f3f4f6; color: #374151;')
        return format_html(
            '<span style="padding: 4px 12px; border-radius: 9999px; font-size: 11px; font-weight: 700; text-transform: uppercase; {}">{}</span>',
            style,
            obj.status
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'


class SeatLayoutAdmin(admin.ModelAdmin):
    list_display = ('route', 'seat_number', 'row_number', 'column_number', 'is_booked')
    search_fields = ('route__id', 'seat_number')
    list_filter = ('is_booked', 'route__date')


# Register all models in admin panel
admin.site.register(User, UserAdmin)
admin.site.register(Bus, BusAdmin)
admin.site.register(Route, RouteAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(SeatLayout, SeatLayoutAdmin)
