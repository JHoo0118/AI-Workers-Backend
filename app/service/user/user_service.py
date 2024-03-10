from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from app.db.prisma import prisma
from app.model.user.user_model import CreateUserInputs, UpdateUserInputs, UserModel


class UserService(object):
    _instance = None
    _ph = PasswordHasher()

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)

        return class_._instance

    def verify_hash(self, plain, hashed) -> bool:
        try:
            return self._ph.verify(hashed, plain)
        except InvalidHashError:
            return False
        except VerifyMismatchError:
            return False

    def get_hash(self, password) -> str:
        return self._ph.hash(password)

    async def create_user(self, create_user_inputs: CreateUserInputs) -> UserModel:
        with prisma.tx() as transaction:
            create_user_inputs.password = self.get_hash(create_user_inputs.password)
            user = transaction.user.create(data=create_user_inputs.model_dump())
            return user

    async def update_user(self, update_user_inputs: UpdateUserInputs) -> UserModel:
        user = prisma.user.update(
            data={
                "username": update_user_inputs.username,
            },
            where={
                "email": update_user_inputs.email,
            },
        )
        return user

    async def get_user(self, email: str) -> UserModel:
        return prisma.user.find_unique(
            where={
                "email": email,
            },
            include={"refreshToken": {"include": {"user": False}}},
        )
