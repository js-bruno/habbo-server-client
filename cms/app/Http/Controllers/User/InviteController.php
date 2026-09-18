<?php

namespace App\Http\Controllers\User;

use App\Http\Controllers\Controller;
use App\Models\Invite;
use App\Models\User;
use App\Rules\WebsiteWordfilterRule;
use App\Services\GameUserMirror;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use Illuminate\View\View;

class InviteController extends Controller
{
    public function __construct(private readonly GameUserMirror $mirror) {}

    /** Show the invite creator (logged-in users). */
    public function index(): View
    {
        $invites = Invite::query()
            ->with('user')
            ->where('inviter_id', Auth::id())
            ->orderByDesc('id')
            ->limit(20)
            ->get();

        return view('user.invite', [
            'invites' => $invites,
        ]);
    }

    /** Generate a fresh invite link. */
    public function store(Request $request): RedirectResponse
    {
        $request->validate([
            'max_uses' => ['nullable', 'integer', 'min:1', 'max:100'],
        ]);

        $invite = Invite::create([
            'code' => $this->uniqueCode(),
            'inviter_id' => Auth::id(),
            'max_uses' => (int) $request->input('max_uses', 1),
        ]);

        return back()->with('generated_invite', $invite);
    }

    /** Public landing: pick a username, the system generates the password. */
    public function show(string $code): View
    {
        $invite = $this->validInvite($code);

        return view('invite', [
            'invite' => $invite,
            'inviter' => $invite->inviter,
        ]);
    }

    /** Redeem: create the account with a generated password, auto-login. */
    public function redeem(Request $request, string $code): RedirectResponse
    {
        $invite = $this->validInvite($code);

        $validated = $request->validate([
            'username' => [
                'required',
                'string',
                sprintf('regex:%s', setting('username_regex') ?: '/^[a-zA-Z0-9_.-]+$/'),
                'max:25',
                Rule::unique('users'),
                new WebsiteWordfilterRule,
            ],
            'terms' => ['required', 'accepted'],
        ]);

        $password = Str::password(10, symbols: false);
        $ip = $request->ip();

        $user = User::create([
            'username' => $validated['username'],
            'password' => Hash::make($password),
            'mail' => null,
            'account_created' => time(),
            'last_login' => time(),
            'motto' => setting('start_motto') ?: 'Welcome to the hotel!',
            'look' => setting('start_look') ?: 'hr-100-61.hd-180-1.ch-210-66.lg-270-110.sh-305-62',
            'credits' => setting('start_credits') ?: 1000,
            'ip_register' => $ip,
            'ip_current' => $ip,
            'auth_ticket' => '',
            'home_room' => (int) (setting('hotel_home_room') ?: 0),
        ]);

        $user->update(['referral_code' => sprintf('%s%s', $user->id, Str::random(8))]);

        // The emulator only reads habbo.users — mirror CMS -> game DB.
        $this->mirror->mirror($user);

        $invite->forceFill([
            'used_by' => $user->id,
            'used_at' => now(),
        ])->save();

        Auth::login($user);

        return redirect()->route('invite.success')->with('invite_credentials', [
            'username' => $user->username,
            'password' => $password,
        ]);
    }

    /** One-time screen showing the generated password + enter client. */
    public function success(): View|RedirectResponse
    {
        $credentials = session('invite_credentials');

        if (! $credentials || ! Auth::check()) {
            return redirect()->route('welcome')->withErrors([
                'invite' => __('Invite session expired, please ask for a new link.'),
            ]);
        }

        session()->forget('invite_credentials');

        return view('invite-success', [
            'username' => $credentials['username'],
            'password' => $credentials['password'],
        ]);
    }

    private function validInvite(string $code): Invite
    {
        $invite = Invite::query()
            ->with('inviter')
            ->where('code', $code)
            ->first();

        if ($invite === null) {
            abort(404, __('This invite link does not exist.'));
        }

        if ($invite->expires_at !== null && $invite->expires_at->isPast()) {
            abort(410, __('This invite link has expired.'));
        }

        $usedCount = $invite->used_by !== null ? 1 : 0;

        if ($usedCount >= $invite->max_uses) {
            abort(410, __('This invite link has already been used.'));
        }

        return $invite;
    }

    private function uniqueCode(): string
    {
        do {
            $code = Str::lower(Str::random(12));
        } while (Invite::where('code', $code)->exists());

        return $code;
    }
}