from django.urls import path

from . import views

urlpatterns = [
    path("csrf/", views.csrf, name="csrf"),
    path("create_or_join_room/", views.create_or_join_room, name="create_or_join_room"),
    path("create_room/", views.create_room, name="create_room"),
    path("join_room/", views.join_room, name="join_room"),
    path("set_board/", views.set_board, name="set_board"),
    path("start_game/", views.start_game, name="start_game"),
    path("night_action/", views.night_action, name="night_action"),
    path("room_state/", views.room_state, name="room_state"),
    path("reveal/", views.reveal, name="reveal"),
    path("vote/", views.vote, name="vote"),
    path("result/", views.result, name="result"),
]