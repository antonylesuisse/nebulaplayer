/*---------------------------------------------------------
 * OpenERP Web chrome
 *---------------------------------------------------------*/
openerp.web.chrome = function(instance, nebula) {
var QWeb = instance.web.qweb,
    _t = instance.web._t;

instance.web.Notification =  instance.web.Widget.extend({
    template: 'Notification',
    init: function() {
        this._super.apply(this, arguments);
        instance.web.notification = this;
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$el.notify({
            speed: 500,
            expires: 2500
        });
    },
    notify: function(title, text, sticky) {
        sticky = !!sticky;
        var opts = {};
        if (sticky) {
            opts.expires = false;
        }
        this.$el.notify('create', {
            title: title,
            text: text
        }, opts);
    },
    warn: function(title, text, sticky) {
        sticky = !!sticky;
        var opts = {};
        if (sticky) {
            opts.expires = false;
        }
        this.$el.notify('create', 'oe_notification_alert', {
            title: title,
            text: text
        }, opts);
    }
});

/**
 * The very minimal function everything should call to create a dialog
 * in OpenERP Web Client.
 */
instance.web.dialog = function(element) {
    var result = element.dialog.apply(element, _.rest(_.toArray(arguments)));
    result.dialog("widget").addClass("openerp");
    return result;
};

instance.web.Dialog = instance.web.Widget.extend({
    dialog_title: "",
    init: function (parent, options, content) {
        var self = this;
        this._super(parent);
        this.content_to_set = content;
        this.dialog_options = {
            modal: true,
            destroy_on_close: true,
            width: 900,
            min_width: 0,
            max_width: '95%',
            height: 'auto',
            min_height: 0,
            max_height: this.get_height('100%') - 200,
            autoOpen: false,
            position: [false, 40],
            buttons: {},
            beforeClose: function () { self.on_close(); },
            resizeStop: this.on_resized
        };
        for (var f in this) {
            if (f.substr(0, 10) == 'on_button_') {
                this.dialog_options.buttons[f.substr(10)] = this[f];
            }
        }
        if (options) {
            _.extend(this.dialog_options, options);
        }
    },
    get_options: function(options) {
        var self = this,
            o = _.extend({}, this.dialog_options, options || {});
        _.each(['width', 'height'], function(unit) {
            o[unit] = self['get_' + unit](o[unit]);
            o['min_' + unit] = self['get_' + unit](o['min_' + unit] || 0);
            o['max_' + unit] = self['get_' + unit](o['max_' + unit] || 0);
            if (o[unit] !== 'auto' && o['min_' + unit] && o[unit] < o['min_' + unit]) o[unit] = o['min_' + unit];
            if (o[unit] !== 'auto' && o['max_' + unit] && o[unit] > o['max_' + unit]) o[unit] = o['max_' + unit];
        });
        if (!o.title && this.dialog_title) {
            o.title = this.dialog_title;
        }
        return o;
    },
    get_width: function(val) {
        return this.get_size(val.toString(), $(window.top).width());
    },
    get_height: function(val) {
        return this.get_size(val.toString(), $(window.top).height());
    },
    get_size: function(val, available_size) {
        if (val === 'auto') {
            return val;
        } else if (val.slice(-1) == "%") {
            return Math.round(available_size / 100 * parseInt(val.slice(0, -1), 10));
        } else {
            return parseInt(val, 10);
        }
    },
    renderElement: function() {
        if (this.content_to_set) {
            this.setElement(this.content_to_set);
        } else if (this.template) {
            this._super();
        }
    },
    open: function(options) {
        if (! this.dialog_inited)
            this.init_dialog();
        var o = this.get_options(options);
        instance.web.dialog(this.$el, o).dialog('open');
        if (o.height === 'auto' && o.max_height) {
            this.$el.css({ 'max-height': o.max_height, 'overflow-y': 'auto' });
        }
        return this;
    },
    init_dialog: function(options) {
        this.renderElement();
        var o = this.get_options(options);
        instance.web.dialog(this.$el, o);
        var res = this.start();
        this.dialog_inited = true;
        return res;
    },
    close: function() {
        this.$el.dialog('close');
    },
    on_close: function() {
        if (this.__tmp_dialog_destroying)
            return;
        if (this.dialog_options.destroy_on_close) {
            this.__tmp_dialog_closing = true;
            this.destroy();
            this.__tmp_dialog_closing = undefined;
        }
    },
    on_resized: function() {
    },
    destroy: function () {
        _.each(this.getChildren(), function(el) {
            el.destroy();
        });
        if (! this.__tmp_dialog_closing) {
            this.__tmp_dialog_destroying = true;
            this.close();
            this.__tmp_dialog_destroying = undefined;
        }
        if (! this.isDestroyed()) {
            this.$el.dialog('destroy');
        }
        this._super();
    }
});

instance.web.CrashManager = instance.web.CallbackEnabled.extend({
    on_rpc_error: function(error) {
        if (error.data.fault_code) {
            var split = ("" + error.data.fault_code).split('\n')[0].split(' -- ');
            if (split.length > 1) {
                error.type = split.shift();
                error.data.fault_code = error.data.fault_code.substr(error.type.length + 4);
            }
        }
        if (error.code === 200 && error.type) {
            this.on_managed_error(error);
        } else {
            this.on_traceback(error);
        }
    },
    on_managed_error: function(error) {
        instance.web.dialog($('<div>' + QWeb.render('CrashManager.warning', {error: error}) + '</div>'), {
            title: "OpenERP " + _.str.capitalize(error.type),
            buttons: [
                {text: _t("Ok"), click: function() { $(this).dialog("close"); }}
            ]
        });
    },
    on_traceback: function(error) {
        var self = this;
        var buttons = {};
        buttons[_t("Ok")] = function() {
            $(this).dialog("close");
        };
        var dialog = new instance.web.Dialog(this, {
            title: "OpenERP " + _.str.capitalize(error.type),
            width: '80%',
            height: '50%',
            min_width: '800px',
            min_height: '600px',
            buttons: buttons
        }).open();
        dialog.$el.html(QWeb.render('CrashManager.error', {session: instance.session, error: error}));
    },
    on_javascript_exception: function(exception) {
        this.on_traceback({
            type: _t("Client Error"),
            message: exception,
            data: {debug: ""}
        });
    },
});

instance.web.Loading = instance.web.Widget.extend({
    template: 'Loading',
    init: function(parent) {
        this._super(parent);
        this.count = 0;
        this.blocked_ui = false;
        var self = this;
        this.request_call = function() {
            self.on_rpc_event(1);
        };
        this.response_call = function() {
            self.on_rpc_event(-1);
        };
        this.session.on_rpc_request.add_first(this.request_call);
        this.session.on_rpc_response.add_last(this.response_call);
    },
    destroy: function() {
        this.session.on_rpc_request.remove(this.request_call);
        this.session.on_rpc_response.remove(this.response_call);
        this.on_rpc_event(-this.count);
        this._super();
    },
    on_rpc_event : function(increment) {
        var self = this;
        if (!this.count && increment === 1) {
            // Block UI after 3s
            this.long_running_timer = setTimeout(function () {
                self.blocked_ui = true;
                instance.web.blockUI();
            }, 3000);
        }

        this.count += increment;
        if (this.count > 0) {
            if (instance.session.debug) {
                this.$el.text(_.str.sprintf( _t("Loading (%d)"), this.count));
            } else {
                this.$el.text(_t("Loading"));
            }
            this.$el.show();
            this.getParent().$el.addClass('oe_wait');
        } else {
            this.count = 0;
            clearTimeout(this.long_running_timer);
            // Don't unblock if blocked by somebody else
            if (self.blocked_ui) {
                this.blocked_ui = false;
                instance.web.unblockUI();
            }
            this.$el.fadeOut();
            this.getParent().$el.removeClass('oe_wait');
        }
    }
});

instance.web.Login =  instance.web.Widget.extend({
    template: "Login",
    remember_credentials: true,

    init: function(parent, params) {
        this._super(parent);
        this.has_local_storage = typeof(localStorage) != 'undefined';
        this.db_list = null;
        this.selected_db = null;
        this.selected_login = null;
        this.params = params || {};

        if (this.params.login_successful) {
            this.on('login_successful', this, this.params.login_successful);
        }

        if (this.has_local_storage && this.remember_credentials) {
            this.selected_db = localStorage.getItem('last_db_login_success');
            this.selected_login = localStorage.getItem('last_login_login_success');
            if (jQuery.deparam(jQuery.param.querystring()).debug !== undefined) {
                this.selected_password = localStorage.getItem('last_password_login_success');
            }
        }
    },
    start: function() {
        var self = this;
        self.$el.find("form").submit(self.on_submit);
        self.$el.find('.oe_login_manage_db').click(function() {
            self.do_action("database_manager");
        });
        var d;
        if (self.params.db) {
            d = self.do_login(self.params.db, self.params.login, self.params.password);
        } else {
            d = self.rpc("/web/database/get_list", {}).done(self.on_db_loaded).fail(self.on_db_failed);
        }
        return d;
    },
    on_db_loaded: function (result) {
        this.db_list = result.db_list;
        this.$("[name=db]").replaceWith(QWeb.render('Login.dblist', { db_list: this.db_list, selected_db: this.selected_db}));
        if(this.db_list.length === 0) {
            this.do_action("database_manager");
        } else if(this.db_list.length === 1) {
            this.$('div.oe_login_dbpane').hide();
        } else {
            this.$('div.oe_login_dbpane').show();
        }
    },
    on_db_failed: function (error, event) {
        if (error.data.fault_code === 'AccessDenied') {
            event.preventDefault();
        }
    },
    on_submit: function(ev) {
        if(ev) {
            ev.preventDefault();
        }
        var db = this.$("form [name=db]").val();
        if (!db) {
            this.do_warn("Login", "No database selected !");
            return false;
        }
        var login = this.$("form input[name=login]").val();
        var password = this.$("form input[name=password]").val();

        this.do_login(db, login, password);
    },
    /**
     * Performs actual login operation, and UI-related stuff
     *
     * @param {String} db database to log in
     * @param {String} login user login
     * @param {String} password user password
     */
    do_login: function (db, login, password) {
        var self = this;
        this.$el.removeClass('oe_login_invalid');
        self.$(".oe_login_pane").fadeOut("slow");
        return this.session.session_authenticate(db, login, password).pipe(function() {
            if (self.has_local_storage) {
                if(self.remember_credentials) {
                    localStorage.setItem('last_db_login_success', db);
                    localStorage.setItem('last_login_login_success', login);
                    if (jQuery.deparam(jQuery.param.querystring()).debug !== undefined) {
                        localStorage.setItem('last_password_login_success', password);
                    }
                } else {
                    localStorage.setItem('last_db_login_success', '');
                    localStorage.setItem('last_login_login_success', '');
                    localStorage.setItem('last_password_login_success', '');
                }
            }
            self.trigger('login_successful');
        },function () {
            self.$(".oe_login_pane").fadeIn("fast", function() {
                self.$el.addClass("oe_login_invalid");
            });
        });
    },
});
instance.web.client_actions.add("login", "instance.web.Login");

/**
 * Client action to reload the whole interface.
 * If params has an entry 'menu_id', it opens the given menu entry.
 */
instance.web.Reload = instance.web.Widget.extend({
    init: function(parent, params) {
        this._super(parent);
        this.menu_id = (params && params.menu_id) || false;
    },
    start: function() {
        var l = window.location;

        var sobj = $.deparam(l.search.substr(1));
        sobj.ts = new Date().getTime();
        var search = '?' + $.param(sobj);

        var hash = l.hash;
        if (this.menu_id) {
            hash = "#menu_id=" + this.menu_id;
        }
        var url = l.protocol + "//" + l.host + l.pathname + search + hash;
        window.location = url;
    }
});
instance.web.client_actions.add("reload", "instance.web.Reload");

/**
 * Client action to go back in breadcrumb history.
 * If can't go back in history stack, will go back to home.
 */
instance.web.HistoryBack = instance.web.Widget.extend({
    init: function(parent, params) {
        if (!parent.history_back()) {
            window.location = '/' + (window.location.search || '');
        }
    }
});
instance.web.client_actions.add("history_back", "instance.web.HistoryBack");

/**
 * Client action to go back home.
 */
instance.web.Home = instance.web.Widget.extend({
    init: function(parent, params) {
        window.location = '/' + (window.location.search || '');
    }
});
instance.web.client_actions.add("home", "instance.web.Home");

instance.web.Client = instance.web.Widget.extend({
    init: function(parent, origin) {
        instance.client = instance.webclient = this;
        this._super(parent);
        this.origin = origin;
    },
    start: function() {
        var self = this;

        this.crashmanager =  new instance.web.CrashManager();
        instance.session.on_rpc_error.add(this.crashmanager.on_rpc_error);
        return instance.session.session_bind(this.origin).pipe(function() {
            var $e = $(QWeb.render(self._template, {}));
            self.replaceElement($e);
            self.bind_events();
            return self.show_common();
        });
    },
    bind_events: function() {
        var self = this;
        this.$el.on('mouseenter', '.oe_systray > div:not([data-tipsy=true])', function() {
            $(this).attr('data-tipsy', 'true').tipsy().trigger('mouseenter');
        });
        this.$el.on('click', '.oe_dropdown_toggle', function(ev) {
            ev.preventDefault();
            var $toggle = $(this);
            var $menu = $toggle.siblings('.oe_dropdown_menu');
            $menu = $menu.size() >= 1 ? $menu : $toggle.find('.oe_dropdown_menu');
            var state = $menu.is('.oe_opened');
            setTimeout(function() {
                // Do not alter propagation
                $toggle.add($menu).toggleClass('oe_opened', !state);
                if (!state) {
                    // Move $menu if outside window's edge
                    var doc_width = $(document).width();
                    var offset = $menu.offset();
                    var menu_width = $menu.width();
                    var x = doc_width - offset.left - menu_width - 2;
                    if (x < 0) {
                        $menu.offset({ left: offset.left + x }).width(menu_width);
                    }
                }
            }, 0);
        });
        instance.web.bus.on('click', this, function(ev) {
            $.fn.tipsy.clear();
            if (!$(ev.target).is('input[type=file]')) {
                self.$el.find('.oe_dropdown_menu.oe_opened, .oe_dropdown_toggle.oe_opened').removeClass('oe_opened');
            }
        });
    },
    show_common: function() {
        var self = this;
        self.notification = new instance.web.Notification(this);
        self.notification.appendTo(self.$el);
        self.loading = new instance.web.Loading(self);
        self.loading.appendTo(self.$el);
        self.action_manager = new instance.web.ActionManager(self);
        self.action_manager.appendTo(self.$('.oe_application'));
    },
    toggle_bars: function(value) {
        this.$('tr:has(td.oe_topbar),.oe_leftbar').toggle(value);
    }
});

instance.web.WebClient = instance.web.Client.extend({
    _template: 'WebClient',
    init: function(parent) {
        this._super(parent);
        this._current_state = null;
    },
    start: function() {
        var self = this;
        console.log("Hello");
        return $.when(this._super()).pipe(function() {

            var n = new instance.web.NebulaPlayer(this);
            n.appendTo(self.$el);
            if (jQuery.param !== undefined && jQuery.deparam(jQuery.param.querystring()).kitten !== undefined) {
                $("body").addClass("kitten-mode-activated");
                if ($.blockUI) {
                    $.blockUI.defaults.message = '<img src="http://www.amigrave.com/kitten.gif">';
                }
            }
            //if (!self.session.session_is_valid()) {
            //    self.show_login();
            //} else {
            //    self.show_application();
            //}
        });
    },
    set_title: function(title) {
        title = _.str.clean(title);
        var sep = _.isEmpty(title) ? '' : ' - ';
        document.title = title + sep + 'OpenERP';
    },
    show_common: function() {
        var self = this;
        this._super();
        window.onerror = function (message, file, line) {
            self.crashmanager.on_traceback({
                type: _t("Client Error"),
                message: message,
                data: {debug: file + ':' + line}
            });
        };
    },
    show_login: function() {
        this.toggle_bars(false);
        
        var action = {
            'type': 'ir.actions.client',
            'tag': 'login'
        };
        var state = $.bbq.getState(true);
        if (state.action === "login") {
            action.params = state;
        }

        this.action_manager.do_action(action);
        this.action_manager.inner_widget.on('login_successful', this, function() {
            this.do_push_state(state);
            this._current_state = null;     // ensure the state will be loaded
            this.show_application();        // will load the state we just pushed
        });
    },
    show_application: function() {
        var self = this;
        self.toggle_bars(true);
        self.menu = new instance.web.Menu(self);
        self.menu.replace(this.$el.find('.oe_menu_placeholder'));
        self.menu.on('menu_click', this, this.on_menu_action);
        self.user_menu = new instance.web.UserMenu(self);
        self.user_menu.replace(this.$el.find('.oe_user_menu_placeholder'));
        self.user_menu.on_menu_logout.add(this.proxy('on_logout'));
        self.user_menu.on_action.add(this.proxy('on_menu_action'));
        self.user_menu.do_update();
        self.bind_hashchange();
        self.set_title();
    },
    destroy_content: function() {
        _.each(_.clone(this.getChildren()), function(el) {
            el.destroy();
        });
        this.$el.children().remove();
    },
    do_reload: function() {
        var self = this;
        return this.session.session_reload().pipe(function () {
            instance.session.load_modules(true).pipe(
                self.menu.proxy('do_reload')); });

    },
    do_notify: function() {
        var n = this.notification;
        n.notify.apply(n, arguments);
    },
    do_warn: function() {
        var n = this.notification;
        n.warn.apply(n, arguments);
    },
    on_logout: function() {
        var self = this;
        this.session.session_logout().then(function () {
            $(window).unbind('hashchange', self.on_hashchange);
            self.do_push_state({});
            window.location.reload();
        });
    },
    bind_hashchange: function() {
        var self = this;
        $(window).bind('hashchange', this.on_hashchange);

        var state = $.bbq.getState(true);
        if (_.isEmpty(state) || state.action == "login") {
            self.menu.has_been_loaded.then(function() {
                var first_menu_id = self.menu.$el.find("a:first").data("menu");
                if(first_menu_id) {
                    self.menu.menu_click(first_menu_id);
                }
            });
        } else {
            $(window).trigger('hashchange');
        }
    },
    on_hashchange: function(event) {
        var self = this;
        var state = event.getState(true);
        if (!_.isEqual(this._current_state, state)) {
            if(state.action_id === undefined && state.menu_id) {
                self.menu.has_been_loaded.then(function() {
                    self.menu.do_reload().then(function() {
                        self.menu.menu_click(state.menu_id)
                    });
                });
            } else {
                this.action_manager.do_load_state(state, !!this._current_state);
            }
        }
        this._current_state = state;
    },
    do_push_state: function(state) {
        this.set_title(state.title);
        delete state.title;
        var url = '#' + $.param(state);
        this._current_state = _.clone(state);
        $.bbq.pushState(url);
    },
    on_menu_action: function(options) {
        var self = this;
        this.rpc("/web/action/load", { action_id: options.action_id })
            .then(function (result) {
                var action = result.result;
                if (options.needaction) {
                    action.context.search_default_needaction_pending = true;
                }
                self.action_manager.clear_breadcrumbs();
                self.action_manager.do_action(action);
            });
    },
    do_action: function(action) {
        var self = this;
        // TODO replace by client action menuclick
        if(action.menu_id) {
            this.do_reload().then(function () {
                self.menu.menu_click(action.menu_id);
            });
        }
    },
    set_content_full_screen: function(fullscreen) {
        if (fullscreen) {
            $(".oe_webclient", this.$el).addClass("oe_content_full_screen");
            $("body").css({'overflow-y':'hidden'});
        } else {
            $(".oe_webclient", this.$el).removeClass("oe_content_full_screen");
            $("body").css({'overflow-y':'scroll'});
        }
    }
});

instance.web.EmbeddedClient = instance.web.Client.extend({
    _template: 'EmbedClient',
    init: function(parent, origin, dbname, login, key, action_id, options) {
        this._super(parent, origin);

        this.dbname = dbname;
        this.login = login;
        this.key = key;
        this.action_id = action_id;
        this.options = options || {};
    },
    start: function() {
        var self = this;
        return $.when(this._super()).pipe(function() {
            return instance.session.session_authenticate(self.dbname, self.login, self.key, true).pipe(function() {
                return self.rpc("/web/action/load", { action_id: self.action_id }, function(result) {
                    var action = result.result;
                    action.flags = _.extend({
                        //views_switcher : false,
                        search_view : false,
                        action_buttons : false,
                        sidebar : false
                        //pager : false
                    }, self.options, action.flags || {});

                    self.action_manager.do_action(action);
                });
            });
        });
    },
});

instance.web.embed = function (origin, dbname, login, key, action, options) {
    $('head').append($('<link>', {
        'rel': 'stylesheet',
        'type': 'text/css',
        'href': origin +'/web/webclient/css'
    }));
    var currentScript = document.currentScript;
    if (!currentScript) {
        var sc = document.getElementsByTagName('script');
        currentScript = sc[sc.length-1];
    }
    var client = new instance.web.EmbeddedClient(null, origin, dbname, login, key, action, options);
    client.insertAfter(currentScript);
};

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
