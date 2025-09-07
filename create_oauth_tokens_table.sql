-- Create table for storing Google OAuth tokens persistently
-- This ensures tokens survive server restarts and deployments

-- Drop existing table if needed (for clean setup)
DROP TABLE IF EXISTS google_oauth_tokens CASCADE;

-- Create the google_oauth_tokens table
CREATE TABLE google_oauth_tokens (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  coach_id UUID NOT NULL,
  coach_email TEXT,
  access_token TEXT NOT NULL,
  refresh_token TEXT,
  expires_in INTEGER DEFAULT 3600,
  token_type TEXT DEFAULT 'Bearer',
  scope TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  
  -- Ensure one token per coach
  CONSTRAINT unique_coach_token UNIQUE(coach_id)
);

-- Create index for faster lookups by coach_id
CREATE INDEX idx_google_oauth_tokens_coach_id ON google_oauth_tokens(coach_id);

-- Create index for token expiration checks
CREATE INDEX idx_google_oauth_tokens_expires_at ON google_oauth_tokens(expires_at);

-- Add RLS policies
ALTER TABLE google_oauth_tokens ENABLE ROW LEVEL SECURITY;

-- Policy for service role to have full access
CREATE POLICY "Service role full access" ON google_oauth_tokens
  FOR ALL TO service_role
  USING (true)
  WITH CHECK (true);

-- Policy to block public access
CREATE POLICY "Block public access" ON google_oauth_tokens
  FOR ALL TO public
  USING (false);

-- Policy to block anonymous access
CREATE POLICY "Block anon access" ON google_oauth_tokens
  FOR ALL TO anon
  USING (false);

-- Policy for authenticated users to see only their own tokens
CREATE POLICY "Users see own tokens" ON google_oauth_tokens
  FOR SELECT TO authenticated
  USING (coach_id::text = auth.uid()::text);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_google_oauth_tokens_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    NEW.expires_at = NOW() + INTERVAL '1 second' * COALESCE(NEW.expires_in, 3600);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at and expires_at
CREATE TRIGGER update_google_oauth_tokens_timestamp
    BEFORE UPDATE ON google_oauth_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_google_oauth_tokens_updated_at();

-- Grant permissions to service role
GRANT ALL ON google_oauth_tokens TO service_role;

-- Comment on table for documentation
COMMENT ON TABLE google_oauth_tokens IS 'Stores Google OAuth tokens for coaches to persist authentication across server restarts';
COMMENT ON COLUMN google_oauth_tokens.coach_id IS 'UUID of the coach who owns this token';
COMMENT ON COLUMN google_oauth_tokens.access_token IS 'Google OAuth access token for API calls';
COMMENT ON COLUMN google_oauth_tokens.refresh_token IS 'Google OAuth refresh token for renewing access';
COMMENT ON COLUMN google_oauth_tokens.expires_at IS 'Timestamp when the access token expires';

-- Insert a test token for development (remove in production)
-- This is just for immediate testing with Coach Thompson
INSERT INTO google_oauth_tokens (
  coach_id,
  coach_email,
  access_token,
  refresh_token,
  expires_in,
  scope
) VALUES (
  '4aaaebb7-26ae-4ca3-90a2-8149c1be66ec',
  'bralinprime28@gmail.com',
  'mock_access_token_for_testing',
  'mock_refresh_token_for_testing',
  3600,
  'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/contacts.readonly'
) ON CONFLICT (coach_id) DO UPDATE SET
  access_token = EXCLUDED.access_token,
  refresh_token = EXCLUDED.refresh_token,
  updated_at = NOW();