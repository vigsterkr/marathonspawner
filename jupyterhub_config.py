import os

c = get_config()

c.JupyterHub.spawner_class = 'marathonspawner.MarathonSpawner'

c.JupyterHub.ip = '0.0.0.0'
c.JupyterHub.hub_ip = '0.0.0.0'
c.JupyterHub.cmd = 'start-singleuser.sh'
c.JupyterHub.cleanup_servers = False

c.MarathonSpawner.app_prefix = 'jupyter'
c.MarathonSpawner.app_image = 'jupyterhub/singleuser'
c.MarathonSpawner.app_prefix = 'jupyter'
c.MarathonSpawner.marathon_host = 'http://leader.mesos:8080'
c.MarathonSpawner.ports = [8000]
c.MarathonSpawner.mem_limit = '2G'
c.MarathonSpawner.cpu_limit = 1

c.JupyterHub.authenticator_class = 'dummyauthenticator.DummyAuthenticator'
