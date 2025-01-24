from django.test import TestCase
from django.contrib.auth.hashers import check_password
from .models import User

# Create your tests here.


class UserModelTest(TestCase):

    def test_password_is_encrypted(self):
        user = User.objects.create(username='john_doe', name='John Doe',
                                   password='password123',
                                   birthday='1990-01-01',
                                   email='john@example.com')
        user_from_db = User.objects.get(username=user.username)

        self.assertNotEqual(user_from_db.password, 'password123')

        self.assertTrue(check_password('password123', user_from_db.password))
