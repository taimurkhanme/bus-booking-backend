import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from api.models import Bus, Route, SeatLayout

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds database with default superuser, buses, routes and seat layouts'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database data...')

        # 1. Create Admin Superuser
        admin_email = 'admin@busbook.com'
        if not User.objects.filter(email=admin_email).exists():
            User.objects.create_superuser(
                username='admin',
                email=admin_email,
                first_name='Admin',
                phone='0300-1234567',
                password='admin123'
            )
            self.stdout.write(self.style.SUCCESS('Superuser created: admin@busbook.com / admin123'))
        else:
            self.stdout.write('Superuser already exists.')

        # 2. Seed Buses
        buses_data = [
            {'name': 'Faisal Movers', 'bus_number': 'FPT-501', 'total_seats': 40, 'bus_type': 'AC', 'amenities': 'Wifi, Charging Point, Water Bottle, AC'},
            {'name': 'Daewoo Express', 'bus_number': 'DX-902', 'total_seats': 40, 'bus_type': 'Sleeper', 'amenities': 'Sleeper berth, Wifi, Charging Point, Blanket'},
            {'name': 'Bilal Travels', 'bus_number': 'BT-303', 'total_seats': 40, 'bus_type': 'Semi-Sleeper', 'amenities': 'Reclining Seats, Charging Point, AC'},
            {'name': 'Yousaf Travels', 'bus_number': 'YT-104', 'total_seats': 40, 'bus_type': 'Non-AC', 'amenities': 'Fan, Standard seats'},
            {'name': 'Waraich Express', 'bus_number': 'WE-404', 'total_seats': 40, 'bus_type': 'AC', 'amenities': 'Wifi, Charging Point, AC'},
        ]

        buses = []
        for b_data in buses_data:
            bus, created = Bus.objects.get_or_create(
                bus_number=b_data['bus_number'],
                defaults=b_data
            )
            if created:
                self.stdout.write(f"Bus created: {bus.name} ({bus.bus_number})")
            buses.append(bus)

        # 3. Seed Routes
        # Let's seed routes spanning Pakistani cities for today, tomorrow, and subsequent days
        cities = ['Karachi', 'Lahore', 'Islamabad', 'Peshawar', 'Quetta', 'Multan', 'Faisalabad']
        
        today = timezone.localtime().date()
        
        routes_data = [
            {'bus': buses[0], 'source': 'Karachi', 'destination': 'Lahore', 'price': 3500.00, 'days_offset': 0, 'hour_dep': 8, 'hour_arr': 20},
            {'bus': buses[1], 'source': 'Lahore', 'destination': 'Islamabad', 'price': 2200.00, 'days_offset': 0, 'hour_dep': 14, 'hour_arr': 19},
            {'bus': buses[2], 'source': 'Islamabad', 'destination': 'Peshawar', 'price': 1200.00, 'days_offset': 0, 'hour_dep': 18, 'hour_arr': 20},
            {'bus': buses[3], 'source': 'Multan', 'destination': 'Faisalabad', 'price': 1500.00, 'days_offset': 1, 'hour_dep': 9, 'hour_arr': 13},
            {'bus': buses[4], 'source': 'Quetta', 'destination': 'Karachi', 'price': 2800.00, 'days_offset': 1, 'hour_dep': 20, 'hour_arr': 6},
            {'bus': buses[0], 'source': 'Karachi', 'destination': 'Islamabad', 'price': 5500.00, 'days_offset': 2, 'hour_dep': 6, 'hour_arr': 22},
            {'bus': buses[1], 'source': 'Lahore', 'destination': 'Karachi', 'price': 4000.00, 'days_offset': 2, 'hour_dep': 19, 'hour_arr': 7},
            {'bus': buses[2], 'source': 'Faisalabad', 'destination': 'Lahore', 'price': 1000.00, 'days_offset': 2, 'hour_dep': 12, 'hour_arr': 14},
            {'bus': buses[3], 'source': 'Peshawar', 'destination': 'Islamabad', 'price': 1100.00, 'days_offset': 3, 'hour_dep': 10, 'hour_arr': 12},
            {'bus': buses[4], 'source': 'Islamabad', 'destination': 'Lahore', 'price': 2000.00, 'days_offset': 3, 'hour_dep': 16, 'hour_arr': 21},
        ]

        for r_data in routes_data:
            offset_date = today + datetime.timedelta(days=r_data['days_offset'])
            
            # Formulate departures and arrivals datetimes
            dep_time = timezone.make_aware(datetime.datetime.combine(
                offset_date,
                datetime.time(hour=r_data['hour_dep'])
            ))
            
            # Check if arrival carries into next day (e.g. overnight trips)
            arr_date = offset_date
            if r_data['hour_arr'] < r_data['hour_dep']:
                arr_date += datetime.timedelta(days=1)
                
            arr_time = timezone.make_aware(datetime.datetime.combine(
                arr_date,
                datetime.time(hour=r_data['hour_arr'])
            ))

            route, created = Route.objects.get_or_create(
                bus=r_data['bus'],
                source=r_data['source'],
                destination=r_data['destination'],
                date=offset_date,
                defaults={
                    'departure_time': dep_time,
                    'arrival_time': arr_time,
                    'price': r_data['price'],
                    'available_seats': r_data['bus'].total_seats,
                    'is_active': True
                }
            )

            if created:
                self.stdout.write(f"Route created: {route.source} to {route.destination} on {route.date}")
                
                # 4. Generate SeatLayout grid for this route
                # 40 seats in rows of 10 and cols of 4
                total_seats_count = route.bus.total_seats
                rows = 10
                cols = 4
                
                for row_idx in range(1, rows + 1):
                    for col_idx in range(1, cols + 1):
                        row_char = chr(64 + row_idx) # 1 -> A, 2 -> B
                        seat_label = f"{row_char}{col_idx}"
                        
                        SeatLayout.objects.create(
                            route=route,
                            seat_number=seat_label,
                            row_number=row_idx,
                            column_number=col_idx,
                            is_booked=False
                        )
                self.stdout.write(f"Generated 40 seat layouts for route ID: {route.id}")

        self.stdout.write(self.style.SUCCESS('Successfully seeded database!'))
