import os
from spacetime import Node
from utils.pcc_models import Register

def init(df, user_agent, fresh):
    reg = df.read_one(Register, user_agent)
    if not reg:
        reg = Register(user_agent, fresh)
        df.add_one(Register, reg)
        df.commit()
        df.push_await()
    while not reg.load_balancer:
        df.pull_await()
        if reg.invalid:
            raise RuntimeError("User agent string is not acceptable.")
        if reg.load_balancer:
            df.delete_one(Register, reg)
            df.commit()
            df.push()
    return reg.load_balancer

def get_cache_server(config, restart):
    init_node = Node(
        init, Types=[Register], dataframe=(config.host, config.port))
    return init_node.start(
        config.user_agent, restart or not os.path.exists(config.save_file))

# # Jasmine - Moved app class to top level to make pickleable
# class App:
#     def __init__(self):
#         self.config = None
    
#     def set_config(self, config):
#         self.config = config

# # Module-level app instance
# _app_instance = None

# def get_app(config):
#     global _app_instance
#     if _app_instance is None:  # Only create a new instance if one doesn't exist
#         _app_instance = App()
#     _app_instance.set_config(config)
    
#     return _app_instance