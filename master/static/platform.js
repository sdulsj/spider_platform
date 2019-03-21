function initPage(pagination) {
    var page_now = pagination.page;
    var page_list = pagination.iter_pages;
    var page_count = pagination.pages;
    var has_prev = pagination.has_prev;
    var has_next = pagination.has_next;

    var html = '';
    if (has_prev) {
        var page_prev = page_now - 1;
        html += '<li><a href="javascript:void(0);" data-id="' + page_prev + '">&laquo;</a></li>';
    }
    //遍历数据添加
    $.each(page_list, function (key, page) {
        if (page) {
            if (page === page_now) {
                html += '<li class="active"><a href="#">' + page + '</a></li>';
            } else {
                html += '<li><a href="javascript:void(0);" data-id="' + page + '">' + page + '</a></li>';
            }
        } else {
            html += '<li class="disabled"><a href="#">&hellip;</a></li>';
        }
    });
    if (has_next) {
        var page_next = page_now + 1;
        html += '<li><a href="javascript:void(0);" data-id="' + page_next + '">&raquo;</a></li>';
    }
    html += '<li><span>页数 ( ' + page_now + '/' + page_count + ' )</span></li>';
    return html
}

function initData(dataList, pageSize = 10, pageNum = 1) {

}

function delData(event) {
    // var id = $(event.relatedTarget).data('id');
    let id = $(this).attr('data-id');
    if (!id) {
        return
    }
    //异步请求
    if (!confirm("确认删除这条信息？")) {
        return;
    }
    $.ajax(
        {
            type: "post",
            async: true,
            url: "./action",
            data: {"act": "del", "id": id},
            cache: false,
            dataType: 'json',
            beforeSend: function () {
                return true;
            },
            success: function (resp) {
                // 状态修改成功，刷新数据
                pageSearch(null, 1);
            },
            error: function (XMLHttpRequest, textStatus, errorThrown) {
                alert("删除数据失败\r\n" + textStatus + "\r\n" + errorThrown);
            },
            complete: function (XMLHttpRequest, textStatus) {
            }
        });
}

function pageSearch(event, pageNum) {
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
            url: "./search",
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


function pageSearch2() {
    var txt = $("#searchString").val();
    if ($.trim(txt) !== "") {
        $("table tbody tr").hide().filter(":contains('" + txt + "')").show();
    } else {
        $("table tbody tr").show();  //.css("background", "#fff")
    }
}

function flashMsg(msg, level) {
    if (!level) {
        level = 'info';
    }
    var callOut = $(".callout ul");
    callOut.empty();
    callOut.append('<li class="callout-' + level + '">' + msg + '</li>');  // info/success/warning/danger
}