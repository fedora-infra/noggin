var bloodhound_users = new Bloodhound({
    datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
        url: '/search/json?username=%QUERY',
        wildcard: '%QUERY'
    }
});

var bloodhound_groups = new Bloodhound({
    datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
        url: '/search/json?group=%QUERY',
        wildcard: '%QUERY'
    }
});

$('#search').typeahead(
    { highlight: true},
    { name: 'users',
    display: 'uid',
    source: bloodhound_users,
    templates: {
        header: '<h5>Users</h5>'
    }
    },
    { name: 'groups',
    display: 'cn',
    source: bloodhound_groups,
    templates: { header: '<h5>Groups</h5>' }
    }
).on('typeahead:selected', function(evt, itm, name) {
var path = name == "users" ? "user" : "group";
var n = path == "group" ? itm.cn : itm.uid;
window.location.href = '/' + path + '/' + n + '/';
});