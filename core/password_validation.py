import re

from django.core.exceptions import ValidationError


class LetterAndNumberPasswordValidator:
    message = 'La contraseña debe contener al menos una letra y un número.'
    code = 'password_no_letter_or_number'

    def validate(self, password, user=None):
        if not re.search(r'[^\W\d_]', password, re.UNICODE) or not re.search(
            r'\d',
            password,
        ):
            raise ValidationError(self.message, code=self.code)

    def get_help_text(self):
        return self.message
