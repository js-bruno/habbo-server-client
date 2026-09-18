<?php

namespace App\Services;

use App\Models\User;
use Illuminate\Support\Facades\DB;

/**
 * Mirrors a CMS user into the Arcturus game database (habbo.users +
 * users_settings + users_currency). The emulator ONLY reads habbo.users —
 * a CMS-only user gets disconnected right after the websocket handshake.
 */
class GameUserMirror
{
    private const CURRENCY_DUCKETS = 0;
    private const CURRENCY_DIAMONDS = 5;

    public function mirror(User $user, int $rank = 1): void
    {
        $tz = DB::connection('game');

        $existing = $tz->table('users')->where('username', $user->username)->value('id');

        if ($existing !== null) {
            $tz->table('users')->where('id', $existing)->update([
                'look' => $user->look,
                'motto' => $user->motto,
                'credits' => $user->credits,
                'rank' => $rank,
                'ip_current' => $user->ip_current,
                'ip_register' => $user->ip_register,
            ]);

            $gameId = $existing;
        } else {
            $gameId = $tz->table('users')->insertGetId([
                'username' => $user->username,
                'real_name' => $user->real_name ?? '',
                'password' => 'LEGACY',
                'mail' => $user->mail,
                'mail_verified' => $user->mail_verified ? '1' : '0',
                'account_created' => $user->account_created,
                'account_day_of_birth' => $user->account_day_of_birth ?? 0,
                'motto' => $user->motto,
                'look' => $user->look,
                'gender' => $user->gender ?? 'M',
                'rank' => $rank,
                'credits' => $user->credits,
                'pixels' => $user->pixels ?? 0,
                'points' => $user->points ?? 0,
                'ip_register' => $user->ip_register,
                'ip_current' => $user->ip_current,
                'home_room' => $user->home_room ?? 0,
            ]);
        }

        // users_settings: enum columns MUST be quoted strings ('0', '-1').
        $settingsExists = $tz->table('users_settings')->where('user_id', $gameId)->exists();

        if (! $settingsExists) {
            $tz->table('users_settings')->insert([
                'user_id' => $gameId,
                'nux' => '0',
                'talent_track_citizenship_level' => '-1',
                'talent_track_helpers_level' => '-1',
                'has_gotten_default_saved_searches' => '0',
            ]);
        }

        // users_currency: duckets (0) + diamonds (5), Atom defaults if missing.
        foreach ([self::CURRENCY_DUCKETS => 5000, self::CURRENCY_DIAMONDS => 100] as $type => $defaultAmount) {
            $amount = $tz->table('users_currency')
                ->where('user_id', $gameId)
                ->where('type', $type)
                ->value('amount');

            if ($amount === null) {
                $tz->table('users_currency')->insert([
                    'user_id' => $gameId,
                    'type' => $type,
                    'amount' => $defaultAmount,
                ]);
            }
        }
    }
}