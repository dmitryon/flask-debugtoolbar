from flask import url_for



class DebugToolbar(object):

    # default config settings
    config = {
        'DEBUG_TB_INTERCEPT_REDIRECTS': True,
        'DEBUG_TB_PANELS': (
            'flask_debugtoolbar.panels.versions.VersionDebugPanel',
#            'flask_debugtoolbar.panels.timer.TimerDebugPanel',
            'flask_debugtoolbar.panels.headers.HeaderDebugPanel',
            'flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel',
            'flask_debugtoolbar.panels.template.TemplateDebugPanel',
            'flask_debugtoolbar.panels.sqlalchemy.SQLAlchemyDebugPanel',
            'flask_debugtoolbar.panels.logger.LoggingPanel',
            'flask_debugtoolbar.panels.performance.PerformanceDebugPanel',
#            'flask_debugtoolbar.panels.profiler.ProfilerDebugPanel',
    
        )
    }

    panel_classes = []

    def __init__(self, request, jinja_env):
        self.jinja_env = jinja_env
        self.request = request
        self.panels = []

        self.template_context = {
            'static_path': url_for('_debug_toolbar.static', filename='')
        }

        self.create_panels()

    @classmethod
    def load_panels(cls, config):
        cls.config.update(config)

        for panel_path in cls.config['DEBUG_TB_PANELS']:
            dot = panel_path.rindex('.')
            panel_module, panel_classname = panel_path[:dot], panel_path[dot+1:]

            mod = __import__(panel_module, {}, {}, [''])
            panel_class = getattr(mod, panel_classname)
            if hasattr(panel_class, 'setup_url_rules'):
                panel_class.setup_url_rules()
            cls.panel_classes.append(panel_class)

    def create_panels(self):
        """
        Populate debug panels
        """
        activated = self.request.cookies.get('fldt_active', '').split(';')

        for panel_class in self.panel_classes:
            panel_instance = panel_class(
                context=self.template_context,
                jinja_env=self.jinja_env)

            if panel_instance.dom_id() in activated:
                panel_instance.is_active = True
            self.panels.append(panel_instance)

    def render_toolbar(self):
        context = self.template_context.copy()
        context.update({'panels': self.panels})

        template = self.jinja_env.get_template('base.html')
        return template.render(**context)


