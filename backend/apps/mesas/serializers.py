from rest_framework import serializers
from apps.mesas.models import Mesa, Solicitud


class MesaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mesa
        fields = ['id', 'numero', 'capacidad', 'estado', 'qr_code']
        read_only_fields = ['qr_code']

    def validate_numero(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'El número de mesa debe ser mayor a 0'
            )
        return value

    def validate_capacidad(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'La capacidad debe ser mayor a 0'
            )
        return value


class SolicitudSerializer(serializers.ModelSerializer):
    mesa_numero = serializers.IntegerField(source='mesa.numero', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    atendida_por = serializers.SerializerMethodField()

    class Meta:
        model = Solicitud
        fields = [
            'id',
            'mesa',
            'mesa_numero',
            'tipo',
            'tipo_display',
            'estado',
            'creada_en',
            'atendida_en',
            'atendida_por'
        ]
        read_only_fields = fields

    def get_atendida_por(self, obj):
        if not obj.atendida_por:
            return None
        return f'{obj.atendida_por.nombre} {obj.atendida_por.apellido}'
