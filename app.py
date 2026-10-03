"""Streamlit entry point. Each browser session gets its own Supabase client."""
import pandas as pd
import re
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
from metadata import FIELDS, GUIDE, normalize, validate, excel_bytes
from pathlib import Path

st.set_page_config(page_title='Corpus Metadata Studio', page_icon='📚', layout='wide')
st.title('Corpus Metadata Studio')
st.caption('Develop, save, and download your corpus metadata.')
google_login_component = components.declare_component(
    'corpus_metadata_google_login', path=str(Path(__file__).parent / 'google_login'))

def clear_session():
    for key in list(st.session_state):
        del st.session_state[key]

def signup_error_message(error, email, password):
    """Show useful Auth feedback without echoing credentials or address."""
    detail = str(error)
    for secret in (email, password):
        if secret:
            detail = detail.replace(secret, '[hidden]')
    detail = re.sub(r'\s+', ' ', detail).strip()[:240]
    lower = detail.lower()
    if 'already registered' in lower or 'already been registered' in lower:
        return 'This email may already have an account. Try the Log in tab.'
    if 'password' in lower and ('weak' in lower or 'length' in lower or 'characters' in lower):
        return 'Supabase rejected the password. Use a stronger password that meets the project’s password requirements.'
    if 'invalid email' in lower or 'email address' in lower and 'invalid' in lower:
        return 'Supabase did not accept this email address. Check its spelling.'
    if 'rate limit' in lower or 'email rate' in lower or 'over_email_send_rate_limit' in lower:
        return 'Supabase has temporarily limited signup emails. Wait a while, or configure a custom SMTP provider in Supabase.'
    if 'signups not allowed' in lower or 'signup is disabled' in lower or 'email provider is disabled' in lower:
        return 'Email signup is disabled in Supabase. Enable email signups under Authentication settings.'
    return f'Supabase signup error: {detail or "No details returned."}'

def auth_error_message(error, email, password):
    """Translate common Supabase login failures into actionable guidance."""
    detail = str(error)
    for secret in (email, password):
        if secret:
            detail = detail.replace(secret, '[hidden]')
    detail = re.sub(r'\s+', ' ', detail).strip()[:240]
    lower = detail.lower()
    if 'email not confirmed' in lower or 'email_not_confirmed' in lower:
        return 'Your account needs email confirmation. Open the Supabase confirmation email, click its link, then try logging in. Check spam if it is missing.'
    if 'invalid login credentials' in lower or 'invalid_credentials' in lower:
        return 'Email or password was not accepted. If you just signed up, confirm your email first; otherwise check both entries.'
    if 'rate limit' in lower or 'over_email_send_rate_limit' in lower:
        return 'Supabase has temporarily limited authentication requests. Wait a while before trying again.'
    if 'timeout' in lower or 'timed out' in lower or 'connection' in lower:
        return 'The app could not reach Supabase in time. Check your internet connection and try again.'
    return f'Supabase login error: {detail or "No details returned."}'

try:
    if 'client' not in st.session_state:
        # NEVER cache this client: authentication must remain session-specific.
        st.session_state.client = create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_KEY'])
    db = st.session_state.client
except Exception:
    st.error('Setup is incomplete. Add the Supabase URL and publishable key in Streamlit Secrets. See README.md.')
    st.stop()

if 'user_id' not in st.session_state:
    st.subheader('Sign in or create an account')
    st.write('Use your Google account. The first sign-in creates your account automatically.')
    google_client_id = st.secrets.get('GOOGLE_CLIENT_ID', '')
    if google_client_id:
        result = google_login_component(
            google_client_id=google_client_id,
            supabase_url=st.secrets['SUPABASE_URL'],
            supabase_key=st.secrets['SUPABASE_KEY'],
            key='google_login',
            default=None,
        )
        if result and result.get('access_token') and result.get('refresh_token'):
            try:
                db.auth.set_session(result['access_token'], result['refresh_token'])
                user = db.auth.get_user().user
                if not user:
                    raise ValueError('Supabase did not return a signed-in user.')
                st.session_state.user_id = user.id
                st.session_state.email = user.email
                st.rerun()
            except Exception:
                st.error('Google sign-in reached Supabase, but the session could not be opened. Check that Google is enabled under Supabase Authentication → Providers.')
        elif result and result.get('error'):
            st.error(f"Google sign-in could not finish: {result['error']}")
    else:
        st.warning('Google sign-in is not configured yet. Add GOOGLE_CLIENT_ID in Streamlit Secrets after completing the Google and Supabase setup in README.md.')

    with st.expander('Use an existing email/password account'):
        st.caption('This is for accounts already created before Google sign-in was enabled. New users should use Google above.')
        with st.form('existing_login'):
            email = st.text_input('Email', key='login_email')
            password = st.text_input('Password', type='password', key='login_password')
            submitted = st.form_submit_button('Log in with email')
        if submitted:
            try:
                response = db.auth.sign_in_with_password({'email': email.strip(), 'password': password})
                if not response.session or not response.user:
                    raise ValueError('No authenticated session')
                st.session_state.user_id = response.user.id
                st.session_state.email = response.user.email
                st.rerun()
            except Exception as error:
                st.error(auth_error_message(error, email.strip(), password))
    st.stop()

# Verify the account on the server; do not trust the UI identity alone.
try:
    user = db.auth.get_user().user
    if not user or user.id != st.session_state.user_id:
        raise ValueError('Session mismatch')
except Exception:
    clear_session()
    st.warning('Your session has ended. Please log in again.')
    st.stop()
uid = user.id
st.sidebar.write(f"Welcome, {(user.user_metadata or {}).get('display_name', 'researcher')}")
st.sidebar.caption(user.email)
if st.sidebar.button('Log out'):
    try:
        db.auth.sign_out()
    finally:
        clear_session()
    st.rerun()

try:
    projects = db.table('corpora').select('id,name').eq('owner_id', uid).order('name').execute().data
except Exception:
    st.error('Could not load your corpora. Check your connection and that setup.sql has been run.')
    st.stop()
with st.sidebar.form('new_corpus'):
    corpus_name = st.text_input('New corpus name', max_chars=120)
    create = st.form_submit_button('Create corpus')
if create:
    if not corpus_name.strip():
        st.sidebar.error('Enter a corpus name.')
    else:
        try:
            db.table('corpora').insert({'name': corpus_name.strip(), 'owner_id': uid}).execute()
            st.rerun()
        except Exception:
            st.sidebar.error('Could not create corpus. The name may already exist.')
if not projects:
    st.info('Create your first corpus using the sidebar.')
    st.stop()
project_map = {p['id']: p['name'] for p in projects}
pid = st.sidebar.selectbox('My corpora', list(project_map), format_func=project_map.get)
st.subheader(project_map[pid])
try:
    # Paginate; Supabase normally caps a single result set.
    records = []
    offset = 0
    while True:
        page = db.table('metadata_records').select('id,data').eq('owner_id', uid).eq('corpus_id', pid).order('id').range(offset, offset + 499).execute().data
        records.extend(page)
        if len(page) < 500:
            break
        offset += 500
except Exception:
    st.error('Could not load metadata. Please try again.')
    st.stop()
st.metric('Saved texts', len(records))
rows = [r['data'] for r in records]
with st.expander('Field guide'):
    st.table(pd.DataFrame({'Field': FIELDS, 'What to enter': GUIDE}))

choice = st.selectbox('Record to edit', ['New record'] + [r['id'] for r in records],
                      format_func=lambda x: x if x == 'New record' else next(r['data']['File_ID'] for r in records if r['id'] == x))
current = {} if choice == 'New record' else next(r['data'] for r in records if r['id'] == choice)
with st.form(f'record_{pid}_{choice}'):
    values = {}
    columns = st.columns(3)
    for i, field in enumerate(FIELDS):
        with columns[i % 3]:
            values[field] = st.text_input(field.replace('_', ' '), value=current.get(field, ''), help=GUIDE[i])
    save = st.form_submit_button('Save record', type='primary')
if save:
    try:
        values = normalize(values)
        validate([values])
        payload = {'owner_id': uid, 'corpus_id': pid, 'file_id': values['File_ID'], 'data': values}
        if choice == 'New record':
            db.table('metadata_records').insert(payload).execute()
        else:
            db.table('metadata_records').update(payload).eq('id', choice).eq('owner_id', uid).eq('corpus_id', pid).execute()
        st.rerun()
    except ValueError as error:
        st.error(str(error))
    except Exception:
        st.error('Could not save. Check the connection and use a unique File ID within this corpus.')

if choice != 'New record':
    with st.expander('Delete selected record'):
        confirmed = st.checkbox('I want to permanently delete this record', key=f'delete_{pid}_{choice}')
        if st.button('Delete record', disabled=not confirmed):
            try:
                db.table('metadata_records').delete().eq('id', choice).eq('owner_id', uid).eq('corpus_id', pid).execute()
                st.rerun()
            except Exception:
                st.error('Deletion failed. Try again.')

st.subheader('Import an existing Excel metadata file')
uploaded = st.file_uploader('Upload .xlsx (up to 5 MB)', type=['xlsx'], key=f'upload_{pid}')
st.caption('Uses the Student Metadata sheet, or the first sheet. Existing File IDs are skipped; new records are added.')
if uploaded and st.button('Import new records'):
    try:
        if uploaded.size > 5 * 1024 * 1024:
            raise ValueError('Maximum upload size is 5 MB.')
        workbook = pd.ExcelFile(uploaded, engine='openpyxl')
        sheet = 'Student Metadata' if 'Student Metadata' in workbook.sheet_names else workbook.sheet_names[0]
        frame = pd.read_excel(workbook, sheet_name=sheet, dtype=str, keep_default_na=False)
        if set(FIELDS) - set(frame.columns):
            raise ValueError('All 12 template columns are required. Download the blank template below.')
        incoming = [normalize(row) for row in frame[FIELDS].to_dict('records') if any(str(v).strip() for v in row.values())]
        if len(incoming) > 2000:
            raise ValueError('Import at most 2,000 rows at a time.')
        validate(incoming)
        existing = {row['File_ID'] for row in rows}
        fresh = [row for row in incoming if row['File_ID'] not in existing]
        if fresh:
            # One insert request is atomic; uniqueness protects simultaneous imports.
            db.table('metadata_records').insert([{'owner_id': uid, 'corpus_id': pid,
                'file_id': row['File_ID'], 'data': row} for row in fresh]).execute()
            st.rerun()
        else:
            st.info('No new records: these File IDs are already saved.')
    except ValueError as error:
        st.error(str(error))
    except Exception:
        st.error('Import failed. Check your workbook, connection, and duplicate File IDs. Refresh before retrying.')

st.subheader('Preview and download')
st.dataframe(pd.DataFrame(rows, columns=FIELDS), hide_index=True, use_container_width=True)
anonymous = st.checkbox('Omit student names and roll numbers from download', value=True)
st.caption('Review Notes and other fields for identifying information before sharing.')
st.download_button('Download my metadata (.xlsx)', excel_bytes(rows, anonymous),
                   file_name='corpus_metadata.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
st.download_button('Download blank template (.xlsx)', excel_bytes([]),
                   file_name='metadata_template.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
