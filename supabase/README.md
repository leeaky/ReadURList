# Apply this SQL in the Supabase SQL editor (or `supabase db push`).

The worker uses `DATABASE_URL=postgresql+psycopg://…`.
The Vercel app uses `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`.
RLS is on with no anon policies; the service role bypasses RLS.
