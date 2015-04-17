BEGIN;
CREATE TABLE "tastypie_apiaccess" (
    "id" serial NOT NULL PRIMARY KEY,
    "identifier" varchar(255) NOT NULL,
    "url" varchar(255) NOT NULL,
    "request_method" varchar(10) NOT NULL,
    "accessed" integer CHECK ("accessed" >= 0) NOT NULL
)
;
CREATE TABLE "tastypie_apikey" (
    "id" serial NOT NULL PRIMARY KEY,
    "user_id" integer NOT NULL UNIQUE REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    "key" varchar(128) NOT NULL,
    "created" timestamp with time zone NOT NULL
)
;
CREATE INDEX "tastypie_apikey_key" ON "tastypie_apikey" ("key");
CREATE INDEX "tastypie_apikey_key_like" ON "tastypie_apikey" ("key" varchar_pattern_ops);
COMMIT;
