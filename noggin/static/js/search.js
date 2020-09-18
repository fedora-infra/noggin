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
        header: "<h5>Users</h5>",
      },
    },
    {
      name: "groups",
      display: "cn",
      source: bloodhound_groups,
      templates: { header: "<h5>Groups</h5>" },
    }
  )
  .on("typeahead:selected", function (evt, itm, name) {
    window.location.href = itm.url;
  });
