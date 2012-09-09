openerp.web.nebula = function(instance) {
var QWeb = instance.web.qweb;

instance.web.Search = instance.web.Widget.extend({
    template: "nebula.Search",
    init: function(parent) {
        this._super(parent);
        this.query = null;
    },
    on_search: function() {
        this.trigger('on_search', arguments);
    },
});

instance.web.PlayList = instance.web.Widget.extend({
    template: "nebula.PlayList",
    events: {
        "clicked": "Playlist item clicked"
    },
    init: function(parent) {
        this._super(parent);
        this.id = 0;
        this.search = new instance.web.Search(this);

        this.records = [];

        this.index = null;

        this.columns = []; // facets that we dediced to display as a column
        this.hidden = ['name']; // facets that we dediced to not display at all
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.search.appendTo(this.$el);
        // load current list
        // set event handlers
        this.rpc('/nebula/playlist', {}).then(this.on_loaded);
        this.$el.on('click', '.np_playlist_play', function(ev) {
            ev.preventDefault();
            var id = $(this).data('id');
            self.trigger('clicked',id)
        });
    },
    on_loaded: function(records) {
        this.records = records;
        var records = QWeb.render('nebula.PlayList.table', { widget: this });
        this.$el.find('table').html(records);
    },
    human_filesize: function(size) {
        var units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        var i = 0;
        while (size >= 1024) {
            size /= 1024;
            ++i;
        }
        return size.toFixed(2) + ' ' + units[i];
    },
});

instance.web.MusicPlayer = instance.web.Widget.extend({
    init: function(parent, playlist) {
        this._super(parent);
    },
    play: function(playlist, id) {
        this.playlist = playlist;
        var url = '/nebula/stream?name=' + escape(id);
        //var player = Player.fromURL('/nebula/stream?name=' + escape(id));
        //player.play();
        if (this.audio) {
            this.audio.pause();
        }
        this.audio = new Audio(url);
        this.audio.play();
        //this.$('audio').remove();
        //var $audio = $('<audio autoplay="autoplay" controls="controls"><source src="' + url + '" type="audio/mpeg"/></audio>');
        //$audio.appendTo(this.$el);
    },
});

instance.web.NebulaPlayer = instance.web.Widget.extend({
    template: "nebula.NebulaPlayer",
    init: function(parent) {
        this._super.apply(this, arguments);
        instance.web.main = this;
        this.playlist = new instance.web.PlayList(this);
        this.musicplayer = new instance.web.MusicPlayer(this);
        this.musicplayer.set({ 'playlist': this.playlist });
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.musicplayer.appendTo(this.$el);
        this.playlist.appendTo(this.$el);
        this.playlist.on('clicked', this, function(id) {
            this.musicplayer.play(this.playlist, id);
        });
    },
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
