from os.path import dirname, join

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

import bdi_api

PROJECT_DIR = dirname(dirname(bdi_api.__file__))


class Settings(BaseSettings):

    local_dir: str = Field(default=join(PROJECT_DIR, "data"), description="For any other value set env variable 'BDI_LOCAL_DIR'")

    model_config = SettingsConfigDict(env_prefix='bdi_')

    @property
    def raw_dir(self) -> str:
        """Store inside all the raw jsons"""
        return join(self.local_dir, "raw")

    @property
    def prepared_dir(self) -> str:
        return join(self.local_dir, "prepared")
