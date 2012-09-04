openerp.web.nebula = function(instance) {
var QWeb = instance.web.qweb;

instance.web.NebulaPlayer = instance.web.Widget.extend({
})

instance.web.NebulaPlayer = instance.web.Widget.extend({
    init: function(parent) {
        this._super(parent);
    },
    start: function() {
        var self = this;
        console.log("Hello");

        var player = Player.fromURL('http://localhost:8090/nebula/static/smp_dpintro.wav');
        player.play();

    },
})

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
