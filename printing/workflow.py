"""Order status workflow (BR-05, BR-10). Keys are plain strings on purpose."""
from .models import PrintOrder

S = PrintOrder.Status

# Shop owner transitions. COMPLETED is reached only by recording the cash payment.
NEXT_STATUSES = {
    S.PENDING.value: [S.PRINTING.value, S.CANCELLED.value],
    S.PRINTING.value: [S.READY.value, S.CANCELLED.value],
    S.READY.value: [S.CANCELLED.value],
    S.COMPLETED.value: [],
    S.CANCELLED.value: [],
}

STUDENT_EDITABLE = (S.PENDING.value,)
STUDENT_DELETABLE = (S.PENDING.value, S.CANCELLED.value)
SHOP_VISIBLE_DOWNLOAD = (
    S.PENDING.value, S.PRINTING.value, S.READY.value, S.COMPLETED.value,
)


def allowed_next(status):
    return NEXT_STATUSES.get(str(status), [])


def next_actions(status):
    """[(value, label)] for the buttons on the shop owner's order page."""
    return [(v, PrintOrder.Status(v).label) for v in allowed_next(status)]
