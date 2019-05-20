from enum import Enum

from peewee import ForeignKeyField, BooleanField, TextField, IntegerField, DateTimeField
from playhouse.postgres_ext import ArrayField, BinaryJSONField
from apphelpers.db.peewee import create_pgdb_pool, create_base_model, created, dbtransaction

from converge import settings


db = create_pgdb_pool(database=settings.DB_NAME)
dbtransaction = dbtransaction(db)
BaseModel = create_base_model(db)


class CommonModel(BaseModel):
    created = created()

    class Meta:
        # In the next major release (Peewee 4.0), legacy_table_names will have a default value of False.
        # We can remove this at the time of upgrading to Peewee 4.0.
        legacy_table_names = False


class Commenter(CommonModel):
    id = IntegerField(index=True, unique=True)
    username = TextField(unique=True)
    name = TextField()
    enabled = BooleanField(default=True)
    badges = ArrayField(default=[])
    bio = TextField(default='')
    web = TextField(null=True)
    verified = BooleanField(default=False)


class Publication(CommonModel):
    name = TextField(null=False)
    domain = TextField(null=False)


class asset_request_statuses(Enum):
    pending = 0
    accepted = 1
    rejected = 2
    cancelled = 3


class Asset(CommonModel):
    id = TextField(primary_key=True, unique=True, index=True)
    url = TextField()
    publication = ForeignKeyField(Publication, null=True)
    open_till = DateTimeField()


class AssetRequest(CommonModel):
    id = TextField(primary_key=True, unique=True, index=True)
    url = TextField()
    publication = ForeignKeyField(Publication, null=True)
    requester = IntegerField(null=True)
    approver = IntegerField(null=True)
    status = IntegerField(null=False, default=asset_request_statuses.pending.value)


class BaseComment(CommonModel):
    commenter = BinaryJSONField()
    commenter_id = IntegerField(null=False)
    editors_pick = BooleanField(default=False, index=True)
    asset = ForeignKeyField(Asset, index=True)
    content = TextField()
    parent = IntegerField(default=0, null=False)
    ip_address = TextField(null=True)


class PendingComment(BaseComment):
    pass


class Comment(BaseComment):
    pass


class RejectedComment(BaseComment):
    note = TextField()


class ArchivedComment(BaseComment):
    pass


class CommenterStats(CommonModel):
    # {count: 0, reported: <int>, accepted: <int>, rejected: <int>}
    commenter = ForeignKeyField(Commenter, index=True)
    comments = IntegerField(default={})
    reported = IntegerField(default={})
    editor_picks = IntegerField(default=0)


class FlaggedReport(CommonModel):
    """
    A genuine comment can be flagged
    Keeping flag records in separate table ensures
        - flagging abuse doesn't slow down the system and moderation
        - lets track abusers independently
    """
    comment = ForeignKeyField(Commenter, null=False)
    reporter = ForeignKeyField(Commenter, null=False)
    accepted = BooleanField(default=False)


class comment_actions(Enum):
    approved = 0
    rejected = 1
    picked = 2


class CommentActionLog(CommonModel):
    comment = IntegerField(null=False)
    action = IntegerField(null=False)
    actor = IntegerField(null=False, default=0)

# Setup helpers

def get_sub_models(model):
    models = []
    for sub_model in model.__subclasses__():
        models.append(sub_model)
        models.extend(get_sub_models(sub_model))
    return models
the_models = get_sub_models(BaseModel)


def setup_db():
    db.create_tables(the_models, fail_silently=True)


def destroy_db():
    for o in the_models[::-1]:
        if o.table_exists():
            o.drop_table()
            print('DROP: ' + o._meta.name)
