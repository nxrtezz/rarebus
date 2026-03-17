def user_can_edit_operator(user, operator):
    if not user.is_authenticated:
        return False

    if user.is_staff:
        return True

    return operator.supervisors.filter(user=user).exists()  