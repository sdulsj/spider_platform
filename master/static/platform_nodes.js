function initData(dataList, pageSize, pageNum) {
    let tBody = $("#tBody");
    let tbHtml = '';
    //遍历数据添加
    $.each(dataList, function (key, data) {
        tbHtml += '<tr>';
        tbHtml += '<td>' + (pageSize * (pageNum - 1) + key + 1) + '</td>';
        tbHtml += '<td>' + data.group_name + '</td>';
        tbHtml += '<td><a href="./detail/' + data.vc_md5 + '">' + data.host_port + '</a></td>';
        tbHtml += '<td>' + data.node_name + '</td>';
        tbHtml += '<td>' + data.username + '</td>';
        tbHtml += '<td>' + data.status + '</td>';
        tbHtml += '<td>' + data.pending + '</td>';
        tbHtml += '<td>' + data.running + '</td>';
        tbHtml += '<td>' + data.finished + '</td>';
        tbHtml += '<td>';
        tbHtml += '<a type="button" class="btn btn-info" data-wrap="' + encodeURI(JSON.stringify(data)) + '" data-toggle="modal" data-target="#nodeModal">Edit</a>';
        tbHtml += '<a type="button" class="btn btn-danger" data-id="' + data.vc_md5 + '">Delete</a>';
        tbHtml += '</td>';
        tbHtml += '</tr>';
    });
    // 装载数据 加载事件
    tBody.empty().append(tbHtml).find('.btn-danger').click(function () {
        let msg = "确定要删除吗？\n\n请确认！";
        return confirm(msg);
    });
    return tbHtml;
}

function pageSearch(event, pageNum) {
    let ajaxUrl = "/node/search";
    //得到查询条件
    let searchString = $("#searchString").val();
    //得到每页显示条数
    let pageSize = $("#pageSize").val();
    //是否关闭异常的查询条件
    let dataType = $("#dataType").val();
    //得到显示第几页
    if (!pageNum) {
        pageNum = 1;
    }

    $.ajax(
        {
            type: "POST",
            async: true,
            url: ajaxUrl,
            data: {"pageNum": pageNum, "pageSize": pageSize, "dataType": dataType, 'keywords': searchString},
            cache: false,
            dataType: 'json',
            beforeSend: function () {
                return true;
            },
            success: function (pagination) {
                if (!pagination) {
                    return  // 失败，请重试
                }
                let dataList = pagination.items;
                let pager = $("#pager");
                pager.empty();
                pager.append(initPage(pagination));
                pager.find('li a').click(function () {
                    pageSearch(null, $(this).attr("data-id"))
                });
                initData(dataList, pageSize, pageNum)
            },
            error: function (XMLHttpRequest, textStatus, errorThrown) {
                alert("请求数据失败\r\n" + textStatus + "\r\n" + errorThrown);
            },
            complete: function (XMLHttpRequest, textStatus) {
            }
        });
}

function showModalNode(event) {
    let wrap = $(event.relatedTarget).data('wrap');
    if (!wrap) {
        return
    }
    let data = JSON.parse(decodeURI(wrap));
    let modal = $(this);
    // 赋值
    modal.find('.modal-title').text("Update Node");  // 更新节点
    modal.find("#group_name").val(data.group_name);
    modal.find("#host_port").val(data.host_port);
    modal.find("#username").val(data.username);
    modal.find("#password").val(data.password);
    modal.find("#recipients").val(data.recipients);
    modal.find("#act").val("upd");
    modal.find("#submit").text("Update");  //更新
    // 将input元素设置为readonly
    modal.find('#host_port').attr("readonly", "readonly");
}

function hideModalNode() {
    // 关闭时还原为add状态Create Client
    let modal = $(this);
    modal.find('.modal-title').text("Create Node");  // 创建节点
    modal.find("#group_name").val(null);
    modal.find("#host_port").val(null);
    modal.find("#username").val(null);
    modal.find("#password").val(null);
    modal.find("#recipients").val(null);
    modal.find("#act").val("add");
    modal.find("#submit").text("Create");  // 创建
    // 将input元素设置为readonly
    modal.find('#host_port').removeAttr("readonly");
}

function getNodeStatus() {
    let ajaxUrl = "/node/detail/status";
    let tBody = $("#tBodyStatus");
    let id = tBody.attr("data-id");
    $.ajax(
        {
            type: "POST",
            async: true,
            url: ajaxUrl,
            data: {"id": id},
            cache: false,
            dataType: 'json',
            beforeSend: function () {
                return true;
            },
            success: function (data) {
                if (!data) {
                    return  // 失败，请重试
                }
                let html = '<tr>';
                html += '<td>' + data.cpu + '</td>';
                html += '<td>' + data.virtual_memory + '</td>';
                html += '<td>' + data.swap_memory + '</td>';
                html += '<td>' + data.disk_usage + '</td>';
                html += '<td>' + data.disk_io_read + '</td>';
                html += '<td>' + data.disk_io_write + '</td>';
                html += '<td>' + data.net_io_sent + '</td>';
                html += '<td>' + data.net_io_receive + '</td>';
                html += "</tr>";
                // 装载数据
                tBody.empty().append(html);
            },
            error: function (XMLHttpRequest, textStatus, errorThrown) {
                alert("请求数据失败\r\n" + textStatus + "\r\n" + errorThrown);
            },
            complete: function (XMLHttpRequest, textStatus) {
            }
        });
}

function initDataException(dataList, pageSize, pageNum) {
    let tBody = $("#tBody");
    let is_closed = parseInt($("#dataType").val());
    let html = '';
    //遍历数据添加
    $.each(dataList, function (key, data) {
        html += '<tr data-id="' + data.vc_md5 + '">';
        html += '<td>' + (pageSize * (pageNum - 1) + key + 1) + '</td>';
        html += '<td>' + data.host_port + '</td>';
        html += '<td>' + data.exc_time + '</td>';
        html += '<td>' + data.exc_level + '</td>';
        html += '<td><div style="width:80px;white-space: nowrap;text-overflow:ellipsis; overflow:hidden;">' + data.exc_message + '</div></td>';
        html += '<td><div style="width:120px;white-space: nowrap;text-overflow:ellipsis; overflow:hidden;">' + data.remark + '</div></td>';
        html += '<td>';
        if (is_closed === 0) {
            html += '<a type="button" class="btn btn-info client-error-edit" data-wrap="' + encodeURI(JSON.stringify(data)) + '" data-toggle="modal" data-target="#errorModal">Close</a>';
        } else {
            html += '<a type="button" class="btn btn-danger" href="/node/exception/delete/' + data.vc_md5 + '">Delete</a>';
        }
        html += '</td>';
        html += '</tr>';
    });
    // 装载数据 加载事件
    tBody.empty().append(html).find('.btn-danger').click(function () {
        let msg = "确定要删除吗？\n\n请确认！";
        return confirm(msg);
    });
    return html;
}

function pageSearchException(event, pageNum) {
    let ajaxUrl = "/node/exception/search";
    //得到查询条件
    let searchString = $("#searchString").val();
    //得到每页显示条数
    let pageSize = $("#pageSize").val();
    //是否关闭异常的查询条件
    let dataType = $("#dataType").val();
    let dataID = $("#tBodyStatus").attr("data-id");
    //得到显示第几页
    if (!pageNum) {
        pageNum = 1;
    }

    $.ajax(
        {
            type: "POST",
            async: true,
            url: ajaxUrl,
            data: {
                "pageNum": pageNum,
                "pageSize": pageSize,
                "dataType": dataType,
                "dataID": dataID,
                'keywords': searchString
            },
            cache: false,
            dataType: 'json',
            beforeSend: function () {
                return true;
            },
            success: function (pagination) {
                if (!pagination) {
                    return  // 失败，请重试
                }
                let dataList = pagination.items;
                let pager = $("#pager");
                pager.empty();
                pager.append(initPage(pagination));
                pager.find('li a').click(function () {
                    pageSearch(null, $(this).attr("data-id"))
                });
                initDataException(dataList, pageSize, pageNum)
            },
            error: function (XMLHttpRequest, textStatus, errorThrown) {
                alert("请求数据失败\r\n" + textStatus + "\r\n" + errorThrown);
            },
            complete: function (XMLHttpRequest, textStatus) {
            }
        });
}

function showModalException(event) {
    let data = JSON.parse(decodeURI($(event.relatedTarget).data('wrap')));
    let modal = $(this);
    modal.find("#vc_md5").val(data.vc_md5);
    modal.find("#host_port").val(data.host_port);
    modal.find("#exc_time").val(data.exc_time);
    modal.find("#exc_level").val(data.exc_level);
    modal.find("#exc_message").val(data.exc_message);
    modal.find("#is_closed").val(data.is_closed);
    modal.find("#remark").val(data.remark);
}

function hideModalException() {
    let modal = $(this);
    modal.find("#host_port").val(null);
    modal.find("#exc_time").val(null);
    modal.find("#exc_level").val(null);
    modal.find("#exc_message").val(null);
    modal.find("#is_closed").val(false);
    modal.find("#remark").val(null);
}