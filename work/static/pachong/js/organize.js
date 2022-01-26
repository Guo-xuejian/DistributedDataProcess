/**
 * Created by Administrator on 2016/8/4.
 */
var setting = {
    view: {
        dblClickExpand: false
    },
    check: {
        enable: true
    },
    callback: {
        onRightClick: OnRightClick
    }
};
var zNodes =[
    {	rid:101	,	id:	10	,pId:101,name:"	所有机构—",open:true,icon:"../img/1_close",nocheck:false,
        children:[
            {id:101, name:"上级机构—", open:true, noR:true,
                children:[
                    {id:101, name:"中级部门一	", noR:false,icon:"../img/1_close"},
                    {id:102, name:"中级部门一	", noR:false,icon:"../img/1_close"}

                ]},
            {id:20, name:"上级部门—", open:true,
                children:[
                    {id:101, name:"中级部门一	", noR:false,icon:"../img/1_close"},
                    {id:102, name:"中级部门一	", noR:false,icon:"../img/1_close"},
                    {id:101, name:"中级部门一	", noR:false,icon:"../img/1_close"},
                    {id:102, name:"中级部门一	", noR:false,icon:"../img/1_close"}
                ]},
            {id:30, name:"上级部门—", open:true,
                children:[
                    {id:101, name:"中级部门一	", noR:false,icon:"../img/1_close"},
                    {id:102, name:"中级部门一	", noR:false,icon:"../img/1_close"},
                    {id:101, name:"中级部门一	", noR:false,icon:"../img/1_close"},
                    {id:102, name:"中级部门一	", noR:false,icon:"../img/1_close"}
                ]},
            {id:30, name:"上级部门—", open:true,
                children:[
                    {id:101, name:"中级部门一	", noR:false,icon:"../img/1_close"},
                    {id:102, name:"中级部门一	", noR:false,icon:"../img/1_close"},
                    {id:101, name:"中级部门一	", noR:false,icon:"../img/1_close"},
                    {id:102, name:"中级部门一	", noR:false,icon:"../img/1_close"}
                ]},
            {id:30, name:"上级部门—", open:true,
                children:[
                    {id:101, name:"中级部门一	", noR:false,icon:"../img/1_close"},
                    {id:102, name:"中级部门一	", noR:false,icon:"../img/1_close"},
                    {id:101, name:"中级部门一	", noR:false,icon:"../img/1_close"},
                    {id:102, name:"中级部门一	", noR:false,icon:"../img/1_close"}
                ]}
        ]
    }
];
function OnRightClick(event, treeId, treeNode) {
    if (!treeNode && event.target.tagName.toLowerCase() != "button" && $(event.target).parents("a").length == 0) {
        zTree.cancelSelectedNode();
        showRMenu("root", event.clientX, event.clientY);
    } else if (treeNode && !treeNode.noR) {
        zTree.selectNode(treeNode);
        showRMenu("node", event.clientX, event.clientY);
    }
}
function showRMenu(type, x, y) {
    $("#rMenu ul").show();
    if (type=="root") {
        $("#m_del").hide();
        $("#m_check").hide();
        $("#m_unCheck").hide();
    } else {
        $("#m_del").show();
        $("#m_check").show();
        $("#m_unCheck").show();
    }
    rMenu.css({"top":y+"px", "left":x+"px", "visibility":"visible"});

    $("body").bind("mousedown", onBodyMouseDown);
}
function hideRMenu() {
    if (rMenu) rMenu.css({"visibility": "hidden"});
    $("body").unbind("mousedown", onBodyMouseDown);
}
function onBodyMouseDown(event){
    if (!(event.target.id == "rMenu" || $(event.target).parents("#rMenu").length>0)) {
        rMenu.css({"visibility" : "hidden"});
    }
}
var addCount = 1;
var zTree, rMenu;
$(document).ready(function(){
    $.fn.zTree.init($("#treeDemo"), setting, zNodes);
    zTree = $.fn.zTree.getZTreeObj("treeDemo");
    rMenu = $("#rMenu");
});