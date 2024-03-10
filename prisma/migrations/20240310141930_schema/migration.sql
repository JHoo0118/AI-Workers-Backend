-- Dumbass migration to fix Supabase morons
--
-- Name: extensions; Type: SCHEMA; Schema: -; Owner: -
--
CREATE SCHEMA IF NOT EXISTS extensions;

CREATE EXTENSION IF NOT EXISTS "vector";

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;

--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--
COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';

CREATE SCHEMA IF NOT EXISTS pgsodium;

CREATE EXTENSION IF NOT EXISTS pgsodium WITH SCHEMA pgsodium;

CREATE SCHEMA IF NOT EXISTS vault;

--
-- Name: vault; Type: SCHEMA; Schema: -; Owner: -
--
--
-- Name: supabase_vault; Type: EXTENSION; Schema: -; Owner: -
--
CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault;

--
-- Name: EXTENSION supabase_vault; Type: COMMENT; Schema: -; Owner: -
--
COMMENT ON EXTENSION supabase_vault IS 'Supabase Vault Extension';