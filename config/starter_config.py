import platform

import yaml


class StarterConfig:

    @staticmethod
    def get_config() -> dict:
        if platform.system() == 'Darwin':
            print('>>>>>>> This is MacOS')
            with open('../config/dev.yaml', "r") as f:
                return yaml.load(f, Loader=yaml.SafeLoader)

        if platform.system() == 'Windows':
            print('>>>>>>> This is Windows')
            with open('../config/prod.yaml', "r") as f:
                return yaml.load(f, Loader=yaml.SafeLoader)

        return {}
