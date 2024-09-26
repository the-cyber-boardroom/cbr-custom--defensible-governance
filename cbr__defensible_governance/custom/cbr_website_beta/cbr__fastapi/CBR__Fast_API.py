from os import environ

import cbr_static
import cbr_web_components

from fastapi                                                                import Request, FastAPI, Response
from fastapi.openapi.docs                                                   import get_swagger_ui_html
from starlette.responses                                                    import RedirectResponse, FileResponse, HTMLResponse
from starlette.staticfiles                                                  import StaticFiles
from cbr_athena.athena__fastapi.FastAPI_Athena                              import FastAPI_Athena
from cbr_shared.cbr_backend.server_requests.S3__Server_Request              import S3__Server_Request
from cbr_shared.cbr_sites.CBR_Site__Shared_Objects                          import cbr_site_shared_objects
from cbr_shared.config.Server_Config__CBR_Website                           import server_config__cbr_website
from cbr_website_beta                                                       import global_vars
from cbr_website_beta.cbr__fastapi.routes.CBR__Site_Info__Routes            import CBR__Site_Info__Routes
from cbr_website_beta.cbr__fastapi__markdown.CBR__Fast_API__Markdown        import CBR__Fast_API__Markdown
from cbr_website_beta.cbr__flask.Flask_Site                                 import Flask_Site
from cbr_website_beta.utils.Env_Vars__With_No_Secrets                       import Env_Vars__With_No_Secrets
from osbot_fast_api.api.Fast_API                                            import Fast_API
from osbot_fast_api.api.Fast_API__Http_Event                                import Fast_API__Http_Event
from osbot_utils.context_managers.capture_duration                          import print_duration
from osbot_utils.decorators.methods.cache_on_self                           import cache_on_self
from osbot_utils.utils.Dev import pprint
from osbot_utils.utils.Files                                                import path_combine
from osbot_utils.utils.Http                                                 import current_host_online
from osbot_utils.utils.Misc                                                 import timestamp_to_str_date, timestamp_utc_now


PATH__SKIP_LOGGING_SERVER_REQUESTS = "/assets"

class CBR__Fast_API(Fast_API):
    name          : str = 'CBR__Fast_API'

    def add_athena(self):
        cbr_athena_app = self.cbr__athena().app()
        self.app().mount("/api", cbr_athena_app)

    def add_cbr_fastapi_markdown(self):
        cbr_fastapi_markdown = self.cbr__fastapi_markdown().app()
        self.app().mount("/markdown", cbr_fastapi_markdown)

    def add_cbr_static_routes(self):
        assets_path = path_combine(cbr_static.path, 'assets')
        self.app().mount("/assets", StaticFiles(directory=assets_path, html=True), name="assets")
        return self

    def add_cbr_static_web_components(self):
        target_folder = cbr_web_components.path
        self.app().mount("/web_components", StaticFiles(directory=target_folder, html=True), name="web_components")
        return self

    def add_flask__cbr_website(self):
        flask_site = self.cbr__flask()
        flask_app  = flask_site.app()
        path       = '/'
        self.add_flask_app(path, flask_app)
        return self

    def all_routes(self):
        return  self.routes_paths(expand_mounts=True)

    def attack_surface(self):                                   # todo: expand to include more metadata about the attack surface (namely the method and any post models)
        routes__fast_api = self.all_routes()
        routes__flask    = self.cbr__flask().all_routes()
        all_routes       = routes__fast_api + routes__flask
        return all_routes

    @cache_on_self
    def cbr__athena(self):
        return FastAPI_Athena().setup()

    @cache_on_self
    def cbr__flask(self):
        return Flask_Site()

    @cache_on_self
    def cbr__fastapi_markdown(self):
        return CBR__Fast_API__Markdown().setup()

    @cache_on_self
    def app(self):
        kwargs = {'docs_url': None }
        return FastAPI(**kwargs)

    def config_http_events(self):
        if False:
            cbr_site_shared_objects.s3_db_server_requests()
            with self.http_events as _:
                _.trace_calls  = server_config__cbr_website.req_traces_enabled()
                _.trace_call_config.trace_capture_start_with = ["cbr"]
                #_.background_tasks.append(self.background_task__log_request_data)                      # don't use this since it has a real-time prob when running AWS lambda
                #_.callback_on_request  = self.fast_api__callback_on_request
                _.callback_on_response = self.fast_api__callback_on_response          # so for now add the logs in sync mode

    def config_server_events(self):
        self.log__setup_started()
        self.log__server_env_vars()

    def log__setup_started(self):
        if server_config__cbr_website.s3_log_requests() and False:
            kwargs = dict(event_data = {'answer' : 42 },
                          event_type = "server_setup"  ,
                          level      = "DEBUG"         ,
                          message    = "setup started" ,
                          server_id  = self.server_id  )
            return self.server_events().log_event(**kwargs)


    def log__server_env_vars(self):
        if server_config__cbr_website.s3_log_requests() and False:
            kwargs = dict(event_data = Env_Vars__With_No_Secrets().create()     ,
                      event_type     = "server_setup"    ,
                      level          = "DEBUG"           ,
                      message        = "server env vars" ,
                      server_id      = self.server_id    )
            return self.server_events().log_event(**kwargs)

    # def fast_api__callback_on_request(self, request_data: Fast_API__Request_Data):
    #     print(f'*** in fast_api__callback_on_request: {request_data}')

    def fast_api__callback_on_response(self, response:Response, request_data: Fast_API__Http_Event):
        try:
            if request_data.http_event_request.path.startswith(PATH__SKIP_LOGGING_SERVER_REQUESTS):         # todo: refactor once we have a need to add more folders to skip or be more granular inside the /assets folder
                #print(f"[CBR_FAST_API] skipping logging: {request_data.http_event_request.path}")          # todo: see if we need to log this skip event
                return
            self.fast_api__set_on_response_headers(response, request_data)
            s3_db = cbr_site_shared_objects.s3_db_server_requests()
            with S3__Server_Request(s3_db=s3_db) as _:
                _.create_from_request_data(request_data)
        except Exception as error:
            print(f"ERROR: [fast_api__callback_on_response] {error}")

    def fast_api__set_on_response_headers(self, response:Response, request_data: Fast_API__Http_Event):
        response.headers.append('cbr__server_id'  , self.server_id                              )
        response.headers.append('cbr__event_id'   , request_data.event_id                       )
        response.headers.append('cbr__info_id'    , request_data.http_event_info.info_id        )
        response.headers.append('cbr__request_id' , request_data.http_event_request.request_id  )
        response.headers.append('cbr__response_id', request_data.http_event_response.response_id)
        response.headers.append('cbr__trace_id'   , request_data.http_event_traces.traces_id    )

    # todo see if we still need this, since it works ok, but has a timing issue when running Lambda functions
    # def background_task__log_request_data(self,request: Request, response: Response):
    #
    #     try:                                                                                        # we need to capture this error since an exception here will bring the server down
    #         from osbot_fast_api.api.Fast_API__Request_Data import Fast_API__Request_Data
    #         request_data: Fast_API__Request_Data
    #         request_data       = request.state.request_data
    #         s3_db              = cbr_site_shared_objects.s3_db_server_requests()
    #         with S3__Server_Request(s3_db=s3_db) as _:
    #             _.create_from_request_data(request_data)
    #     except Exception as error:                                                                  # todo: find a better way to capture this instead of the console out
    #         print(f"[ERROR][background_task__log_request_data]: {error}")

    @cache_on_self
    def server_events(self):
        return cbr_site_shared_objects.s3_db_servers()

    #@cbr_trace_calls(duration_bigger_than=0, include=['osbot_fast_api', 'cbr'])
    def setup(self):
        with print_duration(action_name='setup'):
            self.print_server_startup_message   ()
            self.setup_global_vars              ()
            self.config_server_events           ()
            self.config_http_events             ()
            self.load_secrets_from_s3           ()
            super().setup()
            self.add_athena                     ()
            self.add_cbr_fastapi_markdown       ()
            self.add_cbr_static_routes          ()
            self.add_cbr_static_web_components  ()
            self.add_flask__cbr_website         ()             # this has to be last since it any non-resolved routes will be passed to the flask app
            return self

    def setup_global_vars(self):
        global_vars.fast_api_http_events = self.http_events


    def setup_routes(self):
        self.add_routes(CBR__Site_Info__Routes)
        pass

    def setup_add_root_route(self):
        app = self.app()

        @app.get("/")                                # todo: move this to a separate method
        def read_root():
            return RedirectResponse(url="/web/home")

        @app.get('/favicon.ico')                    # todo: convert the png below to .ico file (also see what are the side effects of returning a png instead of an ico)
        def favicon_ico():
            file_path = path_combine(cbr_static.path, "/assets/cbr/tcb-favicon.png")
            return FileResponse(file_path, media_type="image/png")

        @app.get('/docs', include_in_schema=False)
        async def custom_swagger_ui_html(request: Request) -> HTMLResponse:
            return self.custom_swagger_ui_html(request)

    def load_secrets_from_s3(self):
        with server_config__cbr_website as _:
            server_online = current_host_online()               # can't use _.server_online() due to a circular dependency on cbr_site_info__data
            if _.s3_load_secrets() and  _.aws_enabled() and server_online:          # todo refactor out this load of env vars into separate method/class
                print()
                print("####### Setting up AWS Server Secrets #######")
                print("#######")
                try:
                    import boto3
                    from osbot_utils.utils.Env import load_dotenv
                    from osbot_utils.utils.Files import file_exists
                    from osbot_utils.utils.Files import file_contents
                    session = boto3.Session()
                    s3_client = session.client('s3')
                    s3_bucket = '654654216424--cbr-deploy--eu-west-1'
                    s3_key = 'cbr-custom-websites/dotenv_files/cbr-site-live-qa.env'
                    local_dotenv = '/tmp/cbr-site-live-qa.env'
                    s3_client.download_file(s3_bucket, s3_key, local_dotenv)
                    if file_exists(local_dotenv):
                        load_dotenv(local_dotenv)
                        print("####### OK: Dotenv file loaded from S3")
                    else:
                        print("####### Warning: Dotenv file NOT loaded from S3")
                except Exception as error:
                    print(f"####### Warning: Dotenv file NOT loaded from S3: {error}")
                print("#######")
                print("####### Setting up AWS QA Server #######")
                print()
            # else:
            #     print("data not loaded")
            #     with server_config__cbr_website as _:
            #         load_secrets = _.s3_load_secrets()
            #         aws_enabled  = _.aws_enabled()
            #     print(dict(load_secrets=load_secrets, aws_enabled=aws_enabled, server_online=server_online))

    def print_server_startup_message(self):
        timestamp      = timestamp_utc_now()
        timestamp_date = timestamp_to_str_date(timestamp)
        timestamp_time = timestamp_to_str_date(timestamp)

        print()
        print( "########################################################")
        print(f"#######     Custom Cyber Boardroom for CCL      #######")
        print( "########################################################")
        print(f"####### date     :  {timestamp_date}  ")
        print(f"####### time     :  {timestamp_time}  ")
        print(f"####### server_id:  {self.server_id}  ")
        print("########################################################")

    # todo: refactor to separate class
    def custom_swagger_ui_html(self, request: Request):
        #root       = request.scope.get("root_path")
        app         = self.app()
        title       = 'CBR' + " - Swagger UI"
        openapi_url = '/openapi.json'  # '/api/openapi.json'
        static_url  = '/assets/plugins/swagger'
        favicon     = f"{static_url}/favicon.png"

        return get_swagger_ui_html(openapi_url          = f"{openapi_url}"                     ,
                                   title                = title                                ,
                                   swagger_js_url       = f"{static_url}/swagger-ui-bundle.js" ,
                                   swagger_css_url      = f"{static_url}/swagger-ui.css"       ,
                                   swagger_favicon_url  = favicon                              ,
                                   swagger_ui_parameters = app.swagger_ui_parameters           )


cbr_fast_api = CBR__Fast_API()