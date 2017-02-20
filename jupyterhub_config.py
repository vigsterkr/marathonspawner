import os

c.JupyterHub.spawner_class = 'marathonspawner.MarathonSpawner'

c.JupyterHub.ip = '0.0.0.0'
c.JupyterHub.hub_ip = '0.0.0.0'

# Don't try to cleanup servers on exit - since in general for k8s, we want
# the hub to be able to restart without losing user containers
c.JupyterHub.cleanup_servers = False

c.MarathonSpawner.app_image = 'jupyterhub/singleuser'
c.MarathonSpawner.app_prefix = 'jupyter'
c.MarathonSpawner.marathon_host = 'http://leader.mesos:8080'
c.MarathonSpawner.ports = [8000]
c.MarathonSpawner.mem_limit = '2G'
c.MarathonSpawner.cpu_limit = 1
c.MarathonSpawner.hub_ip_connect = os.environ['HUB_IP_CONNECT']
c.MarathonSpawner.hub_port_connect = os.environ['HUB_PORT_CONNECT']


c.JupyterHub.authenticator_class = 'dummyauthenticator.DummyAuthenticator'
