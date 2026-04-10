from rest_framework import serializers
from apps.mesas.models import Mesa


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