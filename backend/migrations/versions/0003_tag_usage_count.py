"""The database keeps tags.usage_count equal to the number of different users who have the tag on an artwork.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

COUNT = (
    "SELECT count(DISTINCT artworks.user_id) FROM artwork_tags "
    "JOIN artworks ON artworks.id = artwork_tags.artwork_id WHERE artwork_tags.tag_id = {tag_id}"
)
BACKFILL = f"UPDATE tags SET usage_count = ({COUNT.format(tag_id='tags.id')})"


AFFECTED_TAGS = """
    SELECT DISTINCT affected FROM unnest(
        CASE TG_OP WHEN 'INSERT' THEN ARRAY[NEW.tag_id]
                   WHEN 'DELETE' THEN ARRAY[OLD.tag_id]
                   ELSE ARRAY[OLD.tag_id, NEW.tag_id] END
    ) AS affected ORDER BY affected
"""


def upgrade() -> None:
    # The tag rows are locked BEFORE the change. The foreign key check of an insert takes a weaker lock on the tag
    # row; if our lock came after it, two simultaneous inserts would each hold the weaker lock and wait for the
    # stronger one (a deadlock). With the lock first, changes to the same tag run one after the other, and the
    # count made after the change sees the other change.
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION lock_tag_usage_count() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            changed_tag_id integer;
        BEGIN
            FOR changed_tag_id IN {AFFECTED_TAGS}
            LOOP
                PERFORM 1 FROM tags WHERE id = changed_tag_id FOR UPDATE;
            END LOOP;
            RETURN COALESCE(NEW, OLD);
        END
        $$
        """
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION refresh_tag_usage_count() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            changed_tag_id integer;
        BEGIN
            FOR changed_tag_id IN {AFFECTED_TAGS}
            LOOP
                UPDATE tags SET usage_count = ({COUNT.format(tag_id="changed_tag_id")}) WHERE id = changed_tag_id;
            END LOOP;
            RETURN NULL;
        END
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER artwork_tags_lock_tag BEFORE INSERT OR DELETE OR UPDATE OF tag_id ON artwork_tags "
        "FOR EACH ROW EXECUTE FUNCTION lock_tag_usage_count()"
    )
    op.execute(
        "CREATE TRIGGER artwork_tags_usage_count AFTER INSERT OR DELETE OR UPDATE OF tag_id ON artwork_tags "
        "FOR EACH ROW EXECUTE FUNCTION refresh_tag_usage_count()"
    )
    op.execute(BACKFILL)
