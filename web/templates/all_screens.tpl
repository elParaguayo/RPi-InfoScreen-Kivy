% rebase("base.tpl", title="Installed Screens")
<form action="/" method="POST">
<table class="centre">
    <input type="hidden" name="test" value="OK" />
    % for screen in screens:
    <tr>
        <td width="30%">{{screen.capitalize()}}</td>
        <td><button name="submit" type="submit" value="enable+{{screen}}"
            % if screens[screen]["enabled"]:
            disabled
            % end
            >Enable</button></td>
        <td><button name="submit" type="submit" value="disable+{{screen}}"
            % if not screens[screen]["enabled"]:
            disabled
            % end
            >Disable</button></td>
        <td><button name="submit" type="submit" value="configure+{{screen}}">
            Configure</button></td>
        <td><button name="submit" type="submit" value="custom+{{screen}}"
            % if not screens[screen]["web"]:
            disabled
            % end
            >Custom</button></td>
    </tr>
    % end
</table>
</form>
