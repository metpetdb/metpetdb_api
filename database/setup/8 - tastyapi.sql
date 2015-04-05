BEGIN;
CREATE TABLE "tastyapi_groupextra" (
    "id" serial NOT NULL PRIMARY KEY,
    "group_id" integer NOT NULL UNIQUE REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED,
    "group_type" varchar(10) NOT NULL,
    "owner_id" integer REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
)
;
CREATE TABLE "tastyapi_groupaccess" (
    "id" serial NOT NULL PRIMARY KEY,
    "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED,
    "read_access" boolean NOT NULL,
    "write_access" boolean NOT NULL,
    "content_type_id" integer NOT NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED,
    "object_id" integer CHECK ("object_id" >= 0) NOT NULL,
    UNIQUE ("group_id", "content_type_id", "object_id")
)
;
CREATE INDEX "tastyapi_groupextra_owner_id" ON "tastyapi_groupextra" ("owner_id");
CREATE INDEX "tastyapi_groupaccess_group_id" ON "tastyapi_groupaccess" ("group_id");
CREATE INDEX "tastyapi_groupaccess_content_type_id" ON "tastyapi_groupaccess" ("content_type_id");
COMMIT;
