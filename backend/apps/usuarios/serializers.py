from rest_framework import serializers
from apps.usuarios.models import Usuario, Rol


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ['id', 'nombre', 'descripcion']


class UsuarioSerializer(serializers.ModelSerializer):
    rol = RolSerializer(read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'apellido', 'email', 'activo', 'rol']


class CrearUsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    rol_id = serializers.IntegerField()

    class Meta:
        model = Usuario
        fields = ['nombre', 'apellido', 'email', 'password', 'rol_id']

    def validate_rol_id(self, value):
        if not Rol.objects.filter(pk=value).exists():
            raise serializers.ValidationError('El rol no existe')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario