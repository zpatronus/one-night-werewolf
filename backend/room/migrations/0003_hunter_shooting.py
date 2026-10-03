from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("room", "0002_remove_player_fake_role")]
    operations = [
        migrations.AddField(model_name="player", name="shot_target", field=models.CharField(max_length=7, null=True, default=None)),
        migrations.AlterField(model_name="room", name="phase", field=models.CharField(max_length=10, default="waiting", choices=[("waiting", "waiting"), ("op", "op"), ("reveal", "reveal"), ("shoot", "shoot"), ("result", "result")])),
    ]
