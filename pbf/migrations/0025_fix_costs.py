# Generated by Django 4.0.1 on 2023-07-05 13:29

from django.db import migrations

def fix_cost(apps, schema_editor):
    Card = apps.get_model("pbf", "Card")
    card = Card.objects.get(name='Call to Vigilance')
    card.cost = 2
    card.save()
    card = Card.objects.get(name='Coordinated Raid')
    card.cost = 1
    card.save()
    card = Card.objects.get(name='Favors of Story and Season')
    card.cost = 1
    card.save()
    card = Card.objects.get(name='Surrounded by the Dahan')
    card.cost = 0
    card.save()

def unfix_cost(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('pbf', '0024_gameplayer_impending'),
    ]

    operations = [
        migrations.RunPython(fix_cost, unfix_cost),
    ]
