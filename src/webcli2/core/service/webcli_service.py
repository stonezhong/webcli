from typing import Optional, List
import uuid
from sqlalchemy.orm import Session
import bcrypt
import jwt
from pydantic import BaseModel

from webcli2.core.data import User, Thread, Action, DataAccessor, ThreadAction

class ServiceError(Exception):
    pass

class InvalidJWTTOken(ServiceError):
    pass

class JWTTokenPayload(BaseModel):
    email: str
    password_version: int
    sub: str
    uuid: str

##############################################################
# APIs
#     create_user
#     get_user_from_jwt_token
#     login_user
#     generate_user_jwt_token
# 
#     list_threads
#     create_thread
#     get_thread
#     patch_thread
#     delete_thread
#     remove_action_from_thread
#     patch_action
#     patch_thread_action
#     
##############################################################

class WebCLIService:
    public_key:str
    private_key:str
    session:Session
    da:DataAccessor

    def __init__(self, *, public_key:str, private_key:str, session:Session):
        self.public_key = public_key
        self.private_key = private_key
        self.session = session
        self.da = DataAccessor(self.session)


    def _hash_password(self, password:str) -> str:
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed_password.decode("utf-8")

    ##############################################################
    # Below are APIs
    ##############################################################
    def create_user(self, *, email:str, password:str) -> User:
        """ Create a new user.
        """
        user = self.da.create_user(
            email = email, 
            password_hash=self._hash_password(password)
        )
        return user

    def get_user_from_jwt_token(self, jwt_token:str) -> User:
        """ Get user from JWT token.
        """
        try:
            payload = jwt.decode(jwt_token, self.public_key, algorithms=["RS256"])
        except jwt.exceptions.InvalidSignatureError as e:
            raise InvalidJWTTOken() from e
        
        jwt_token_payload = JWTTokenPayload.model_validate(payload)
        user_id = int(jwt_token_payload.sub)
        user = self.da.get_user(user_id)
        return user

        
    def login_user(self, *, email:str, password:str) -> Optional[User]:
        """ Login user.
        Returns:
            None if user failed to login. Otherwise, a user object is returned.
        """
        user = self.da.find_user_by_email(email)
        if user is None:
            return None
        
        if bcrypt.checkpw(password.encode("utf-8"), user.hashed_password.encode("utf-8")):
            return user
        else:
            return None
    
    def generate_user_jwt_token(self, user:User)->str:
        """ Generate user JWT token.
        Returns:
            None if user failed to login. Otherwise, a user object is returned.
        """
        payload = JWTTokenPayload(
            email = user.email,
            password_version = user.password_version,
            sub = str(user.id),
            uuid = str(uuid.uuid4())
        )
        jwt_token = jwt.encode(
            payload.model_dump(mode='json'), 
            self.private_key, 
            algorithm="RS256"
        )
        return jwt_token
    
    def list_threads(self, *, user:User) -> List[Thread]:
        """List all thread owned by user.
        """
        return self.da.list_threads(user=user)

    def create_thread(self, *, title:str, description:str, user:User) -> Thread:
        """Create a new thread.
        """
        return self.da.create_thread(title=title, description=description, user=user)

    def get_thread(self, thread_id:int, *, user:User) -> Thread:
        """Retrive a thread.
        """
        return self.da.get_thread(thread_id, user=user)

    def patch_thread(
        self, 
        thread_id:int, 
        *, 
        user:User,
        title:Optional[str]=None, 
        description:Optional[str]=None
    ) -> Thread:
        """Update a thread's title and/or description.
        """
        return self.da.patch_thread(thread_id, title=title, description=description, user=user)

    def delete_thread(self, thread_id:int, *, user:User):
        """Delete a thread.
        """
        return self.da.delete_thread(thread_id, user=user)

    def remove_action_from_thread(
        self, 
        *,
        action_id:int, 
        thread_id:int,
        user:User
    ) -> bool:
        """Remove an action from a thread, it does not delete the action.

        Returns:
            bool: True if the action is removed, False if the action was not part of the thread
        """
        return self.da.remove_action_from_thread(action_id=action_id, thread_id=thread_id, user=user)
        
    def patch_action(self, action_id:int, *, user:User, title:Optional[str]=None) -> Action:
        """Update action's title.
        """
        return self.da.patch_action(action_id, user=user, title=title)

    def patch_thread_action(
        self, 
        thread_id:int, 
        action_id:int, 
        *, 
        user:User,
        show_question:Optional[bool]=None, 
        show_answer:Optional[bool]=None
    ) -> ThreadAction:
        return self.da.patch_thread_action(
            thread_id, 
            action_id, 
            user=user, 
            show_question=show_question, 
            show_answer=show_answer
        )
