"""Work around python-xlib + Mutter Xwayland: cookies use an empty display field.

Mutter writes MIT-MAGIC-COOKIE entries with the display number bytes empty (b''),
while Xlib.support.unix_connect looks up str(dispno).encode() (e.g. b'0' for :0).
No match is found, so the client sends no auth and the server replies with
"Authorization required, but no authorization protocol specified".
"""


def apply_patch():
    from Xlib import error as xerror
    from Xlib import xauth

    if getattr(xauth.Xauthority, "_coc_mutter_disp_patch", False):
        return

    _orig_get_best = xauth.Xauthority.get_best_auth

    def get_best_auth(self, family, address, dispno, types=(b"MIT-MAGIC-COOKIE-1",)):
        try:
            return _orig_get_best(self, family, address, dispno, types=types)
        except xerror.XNoAuthError:
            pass
        num = str(dispno).encode()
        address_b = address.encode() if isinstance(address, str) else address
        matches = {}
        for efam, eaddr, enum, ename, edata in self.entries:
            if efam == family and eaddr == address_b and (enum == num or enum == b""):
                matches[ename] = edata
        for t in types:
            try:
                return (t, matches[t])
            except KeyError:
                pass
        raise xerror.XNoAuthError((family, address_b, dispno))

    xauth.Xauthority.get_best_auth = get_best_auth
    xauth.Xauthority._coc_mutter_disp_patch = True
