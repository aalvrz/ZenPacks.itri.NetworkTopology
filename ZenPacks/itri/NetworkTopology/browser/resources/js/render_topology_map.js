Ext.onReady(function(){

  // Error Flares
  var show_error = Zenoss.flares.Manager.error;

  var map_panel = Ext.create('Ext.panel.Panel', {
    flex: 1
  });

  var refresh_map = function() {
    d3.select("svg").remove();
    render_map(map_panel, sidebar.getValues()['root_id']);
  };


  var sidebar = Ext.create('Ext.form.Panel', {
    id: 'network_topology_form',
    width: 300,
    bodyPadding: 10,
    frame: true,
    defaultType: 'textfield',
    layout: {
      type: 'vbox',
      padding: 5,
      align: 'stretch'
    },
    items: [
      {
        id: 'sidebar_switch_id_label',
        name: 'switch_id_label',
        value: 'Switch IP',
        xtype: 'displayfield'
      },
      {
        id: 'sidebar_switch_id',
        fieldlabel: 'Switch ID',
        name: 'root_id',
        xtype: 'combo',
        valueField: 'name',
        displayField: 'name',
        store: new Ext.data.DirectStore({
          directFn: Zenoss.remote.DeviceRouter.getDeviceUuidsByName,
          root: 'data',
          model: 'Zenoss.model.BasicUUID',
          remoteFilter: true
        }),
        minChars: 3,
        typeAhead: false,
        hideLabel: true,
        hideTrigger: false,
        listConfig: {
          loadingText: 'Searching...',
          emptyText: 'No matching switches found.'
        },
        pageSize: 10
      },
      {
        text: 'Apply',
        name: 'refresh_button',
        xtype: 'button',
        handler: refresh_map
      }
    ]
  });

  var hbox_center_panel = Ext.create('Ext.panel.Panel', {
    layout: {
      type: 'hbox',
      pack: 'start',
      align: 'stretch'
    }
  });
 
  hbox_center_panel.add(sidebar);
  hbox_center_panel.add(map_panel);    
  Ext.getCmp('center_panel').add(hbox_center_panel);

  function render_map(panel, switch_ip) {

  // First get the switch data
  Zenoss.remote.DeviceRouter.getComponents({uid: '/zport/dmd/Devices/Network/Switch/devices/' + switch_ip, limit: 1000, keys: ['local_ip', 'remote_ip', 'remote_type']}, function(result) {
    var width = 1600,
        height = 900;

    var force = d3.layout.force()        
        .size([width, height])
        .linkDistance(200)
        .charge(-800)
        .gravity(0.06)

    var drag = force.drag()
        .on("dragstart", dragstart);

    var svg = d3.select("#" + panel.body.id).append("svg")
        .attr("width", width)
        .attr("height", height);

    var links = result.data;
    var nodes = {};

    // Compute the distinct nodes from the links.
    links.forEach(function(link) {
      link.source = nodes[link.local_ip] || (nodes[link.local_ip] = {name: link.local_ip, type: "switch"});
      link.target = nodes[link.remote_ip] || (nodes[link.remote_ip] = {name: link.remote_ip, type: link.remote_type});
    });

    force
          .links(links)
          .nodes(d3.values(nodes))
          .on("tick", tick)
          .start();

    var link = svg.selectAll(".link")
        .data(force.links())
      .enter().append("line")
        .attr("class", "link");

    var node = svg.selectAll(".node")
        .data(force.nodes())
      .enter().append("g")
        .attr("class", "node")
        .on("dblclick", dblclick)
        .call(drag);

    node.append("image")
        .attr("x", -16)
        .attr("y", -16)
        .attr("width", 32)
        .attr("height", 32)
        .attr("xlink:href", function(d) { return "/++resource++networktopology/img/" + d.type.toLowerCase() + ".png"; });

    node.append("text")
        .attr("dx", -30)
        .attr("dy", 30)
        .text(function(d) { return d.name; });

    function tick() {
      link.attr("x1", function(d) { return d.source.x; })
          .attr("y1", function(d) { return d.source.y; })
          .attr("x2", function(d) { return d.target.x; })
          .attr("y2", function(d) { return d.target.y; });

      node.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });
    }
    
    function dragstart(d) {
      d3.select(this).classed("fixed", d.fixed = true);
    }
    
    function dblclick(d) {
      d3.select(this).classed("fixed", d.fixed = false);
    }
  });
  }
});
