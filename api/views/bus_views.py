from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from ..models import Bus, Route, SeatLayout
from ..serializers import BusSerializer, RouteSerializer, SeatLayoutSerializer

class BusSearchView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        source = request.query_params.get('source')
        destination = request.query_params.get('destination')
        date = request.query_params.get('date')

        print(f"\n--- BUS SEARCH REQUEST ---")
        print(f"Searching for: source='{source}', destination='{destination}', date='{date}'")

        # Log all routes in the DB for comparison
        all_routes = Route.objects.all()
        print(f"Total routes in DB: {all_routes.count()}")
        for r in all_routes:
            print(f" - Route ID {r.id}: {r.source} -> {r.destination} on date={r.date} (active={r.is_active}, seats={r.available_seats})")

        if not source or not destination or not date:
            print("Error: Missing query parameters")
            return Response({
                'success': False,
                'error': 'Query parameters source, destination and date are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Filter active routes connecting cities on specific dates with seats available
        routes = Route.objects.filter(
            source__iexact=source,
            destination__iexact=destination,
            date=date,
            available_seats__gt=0,
            is_active=True
        )
        print(f"Matching routes found: {routes.count()}")
        print(f"---------------------------\n")

        serializer = RouteSerializer(routes, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class BusListView(APIView):
    # GET /api/buses/ - List active/all buses
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            buses = Bus.objects.all()
        else:
            buses = Bus.objects.filter(is_active=True)
        serializer = BusSerializer(buses, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Permission denied. Staff access required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = BusSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class BusDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        bus = get_object_or_404(Bus, pk=pk)
        serializer = BusSerializer(bus)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class RouteListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            routes = Route.objects.all()
        else:
            routes = Route.objects.filter(is_active=True)
        serializer = RouteSerializer(routes, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Permission denied. Staff access required.'
            }, status=status.HTTP_403_FORBIDDEN)
            
        serializer = RouteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        return Response({
            'success': False,
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class RouteDetailView(APIView):
    permission_classes = [permissions.AllowAny] # Allow any so guest checkout can load details

    def get(self, request, pk):
        route = get_object_or_404(Route, pk=pk)
        serializer = RouteSerializer(route)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class RouteSeatsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        route = get_object_or_404(Route, pk=pk)
        seats = SeatLayout.objects.filter(route=route)
        
        serializer = SeatLayoutSerializer(seats, many=True)
        
        total_seats = route.bus.total_seats
        available_seats = seats.filter(is_booked=False).count()

        return Response({
            'success': True,
            'data': {
                'total_seats': total_seats,
                'available': available_seats,
                'seats': serializer.data
            }
        }, status=status.HTTP_200_OK)


class CityListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        sources = Route.objects.filter(is_active=True).values_list('source', flat=True)
        destinations = Route.objects.filter(is_active=True).values_list('destination', flat=True)
        # Combine and unique
        cities = sorted(list(set(list(sources) + list(destinations))))
        return Response({
            'success': True,
            'data': cities
        }, status=status.HTTP_200_OK)
