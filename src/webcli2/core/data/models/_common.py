from pydantic import BaseModel

#######################################################################################################
# Core models are pydantic models
# DB models are SQLALchemy models
# Usually a core models's field data come from one or more DB model, but when we create core model
# we copy all values to core model, core model can work without db model, without db session once 
# core model is instantiated 
#######################################################################################################
# all core models must derived from this
class CoreModelBase(BaseModel):
    pass
