# jquery.dirty

A jQuery plugin to determine when a form has been modified (dirtied) and act accordingly

All state information about the form is held in the data object for the form rather than adding `data-` attributes to the DOM

# Gitter

[https://gitter.im/jquerydirty/Lobby](https://gitter.im/jquerydirty/Lobby)


# Usage

`$("#myForm").dirty();`

# Options
* `preventLeaving` - boolean indicating whether on not to show a warning if the user attempts to navigate away from the form with pending changes

    * Default: false
* `leavingMessage` - message to display when preventLeaving is true

    * Default: 'There are unsaved changes on this page which will be discarded if you continue.'
* `onDirty` - function called when form is modified

* `onClean` - function called when form is restored to original state

# Methods
`$("#myForm").dirty("isDirty");` returns true if a form has been modified

`$("#myForm").dirty("isClean");` returns true if a form has not been modified

`$("#myForm").dirty("refreshEvents");` remove and reapply events. Can be used if content is dynamically added to form

`$("#myForm").dirty("resetForm");` reset the form to the original state when `$("#myForm").dirty();` was called

`$("#myForm").dirty("setAsClean");` set the current state of the formas the 'clean' state. Calling `resetForm` after this will restore the form to the state when `setAsClean`was called

`$("#myForm").dirty("showDirtyFields");` returns jQuery array of all modified fields in the form

# Credits
Thanks to Tomasz Świenty for feedback and a fix for an issue where a value could resolve as `null`
