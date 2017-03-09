import time
import socket
from urllib.parse import urlparse, urlunparse

from textwrap import dedent
from tornado import gen
from traitlets import Any, Integer, List, Unicode, default

from marathon import MarathonClient
from marathon.models.app import MarathonApp, MarathonHealthCheck
from marathon.models.container import MarathonContainerPortMapping, \
    MarathonContainer, MarathonContainerVolume, MarathonDockerContainer
from marathon.models.constraint import MarathonConstraint
from jupyterhub.spawner import Spawner

from .volumenaming import default_format_volume_name


class MarathonSpawner(Spawner):

    app_image = Unicode("jupyterhub/singleuser", config=True)

    app_prefix = Unicode(
        "jupyter",
        help=dedent(
            """
            Prefix for app names. The full app name for a particular
            user will be <prefix>/<username>.
            """
        )
    ).tag(config=True)

    marathon_host = Unicode(
        u'',
        help="Hostname of Marathon server").tag(config=True)

    marathon_constraints = List(
        [],
        help='Constraints to be passed through to Marathon').tag(config=True)

    ports = List(
        [8888],
        help='Ports to expose externally'
        ).tag(config=True)

    volumes = List(
        [],
        help=dedent(
            """
            A list in Marathon REST API format for mounting volumes into the docker container.
            [
                {
                    "containerPath": "/foo",
                    "hostPath": "/bar",
                    "mode": "RW"
                }
            ]

            Note that using the template variable {username} in containerPath,
            hostPath or the name variable in case it's an external drive
            it will be replaced with the current user's name.
            """
        )
    ).tag(config=True)

    network_mode = Unicode(
        'BRIDGE',
        help="Enum of BRIDGE or HOST"
        ).tag(config=True)

    hub_ip_connect = Unicode(
        "",
        help="Public IP address of the hub"
        ).tag(config=True)

    hub_port_connect = Integer(
        -1,
        help="Public PORT of the hub"
        ).tag(config=True)

    format_volume_name = Any(
        help="""Any callable that accepts a string template and a Spawner
        instance as parameters in that order and returns a string.
        """
    ).tag(config=True)

    @default('format_volume_name')
    def _get_default_format_volume_name(self):
        return default_format_volume_name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.mem_limit is None:
            self.mem_limit = '1G'
        self.marathon = MarathonClient(self.marathon_host)

    @property
    def container_name(self):
        return '/%s/%s' % (self.app_prefix, self.user.name)

    def get_state(self):
        state = super().get_state()
        state['container_name'] = self.container_name
        return state

    def load_state(self, state):
        if 'container_name' in state:
            pass

    def get_health_checks(self):
        health_checks = []
        health_checks.append(MarathonHealthCheck(
            protocol='TCP',
            port_index=0,
            grace_period_seconds=300,
            interval_seconds=60,
            timeout_seconds=20,
            max_consecutive_failures=0
            )
        )
        return health_checks

    def get_volumes(self):
        volumes = []
        for v in self.volumes:
            mv = MarathonContainerVolume.from_json(v)
            mv.container_path = self.format_volume_name(mv.container_path, self)
            mv.host_path = self.format_volume_name(mv.host_path, self)
            if mv.external and 'name' in mv.external:
                mv.external['name'] = self.format_volume_name(mv.external['name'], self)
            volumes.append(mv)
        return volumes

    def get_port_mappings(self):
        port_mappings = []
        for p in self.ports:
            port_mappings.append(
                MarathonContainerPortMapping(
                    container_port=p,
                    host_port=0,
                    protocol='tcp'
                )
            )
        return port_mappings

    def get_constraints(self):
        constraints = []
        for c in self.marathon_constraints:
            constraints.append(MarathonConstraint.from_json(c))

    def get_ip_and_port(self):
        app = self.marathon.get_app(self.container_name, embed_tasks=True)
        assert len(app.tasks) == 1

        ip = socket.gethostbyname(app.tasks[0].host)
        return (ip, app.tasks[0].ports[0])

    def _public_hub_api_url(self):
        uri = urlparse(self.hub.api_url)
        port = self.hub_port_connect if self.hub_port_connect > 0 else uri.port
        ip = self.hub_ip_connect if self.hub_ip_connect else uri.hostname
        return urlunparse((
            uri.scheme,
            '%s:%s' % (ip, port),
            uri.path,
            uri.params,
            uri.query,
            uri.fragment
            )
        )

    def get_env(self):
        env = super(MarathonSpawner, self).get_env()
        env.update(dict(
            # Jupyter Hub config
            JPY_USER=self.user.name,
            JPY_COOKIE_NAME=self.user.server.cookie_name,
            JPY_BASE_URL=self.user.server.base_url,
            JPY_HUB_PREFIX=self.hub.server.base_url,
        ))

        if self.notebook_dir:
            env['NOTEBOOK_DIR'] = self.notebook_dir

        if self.hub_ip_connect or self.hub_port_connect > 0:
            hub_api_url = self._public_hub_api_url()
        else:
            hub_api_url = self.hub.api_url
        env['JPY_HUB_API_URL'] = hub_api_url
        return env

    @gen.coroutine
    def start(self):
        docker_container = MarathonDockerContainer(
            image=self.app_image,
            network=self.network_mode,
            port_mappings=self.get_port_mappings())

        app_container = MarathonContainer(
            docker=docker_container,
            type='DOCKER',
            volumes=self.get_volumes())

        # the memory request in marathon is in MiB
        mem_request = self.mem_limit / 1024.0 / 1024.0
        app_request = MarathonApp(
                id=self.container_name,
                env=self.get_env(),
                cpus=self.cpu_limit,
                mem=mem_request,
                container=app_container,
                constraints=self.get_constraints(),
                health_checks=self.get_health_checks(),
                instances=1
            )

        try:
            app = self.marathon.create_app(self.container_name, app_request)
            if app is False:
                return None
        except:
            return None

        for i in range(self.start_timeout):
            running = yield self.poll()
            if running is None:
                ip, port = self.get_ip_and_port()
                self.user.server.ip = ip
                self.user.server.port = port
                return (ip, port)
            time.sleep(1)
        return None

    @gen.coroutine
    def stop(self, now=False):
        self.marathon.delete_app(self.container_name)
        return

    @gen.coroutine
    def poll(self):
        try:
            app = self.marathon.get_app(self.container_name)
        except Exception as e:
            return ""
        else:
            if app.tasks_healthy == 1:
                return None
            return ""
