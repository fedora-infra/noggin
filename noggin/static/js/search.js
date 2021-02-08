var bloodhound_users = new Bloodhound({
  datumTokenizer: Bloodhound.tokenizers.obj.whitespace("value"),
  queryTokenizer: Bloodhound.tokenizers.whitespace,
  remote: {
    url: URL_SEARCH + "?username=%QUERY",
    wildcard: "%QUERY",
  },
});

var bloodhound_groups = new Bloodhound({
  datumTokenizer: Bloodhound.tokenizers.obj.whitespace("value"),
  queryTokenizer: Bloodhound.tokenizers.whitespace,
  remote: {
    url: URL_SEARCH + "?group=%QUERY",
    wildcard: "%QUERY",
  },
});

$("#search")
  .typeahead(
    { highlight: true },
    {
      name: "users",
      display: "uid",
      source: bloodhound_users,
      templates: {
        header: "<h5 class='mb-0'>"+USERS_SEARCH_LABEL+"</h5>",
        pending: "<h5 class='mb-0'>"+USERS_SEARCH_LABEL+"</h5><h5 class='text-center'><i class='fa fa-circle-o-notch fa-spin fa-fw'></i></h5>"
      },
    },
    {
      name: "groups",
      display: "cn",
      source: bloodhound_groups,
      templates: { 
        header: "<h5 class='mb-0'>"+GROUPS_SEARCH_LABEL+"</h5>",
        pending: "<h5 class='mb-0'>"+GROUPS_SEARCH_LABEL+"</h5><h5 class='text-center'><i class='fa fa-circle-o-notch fa-spin fa-fw'></i></h5>"
      },
    }
  )
  .on("typeahead:selected", function (evt, itm, name) {
    window.location.href = itm.url;
  });
