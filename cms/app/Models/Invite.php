<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Support\Carbon;

/**
 * @property int $id
 * @property string $code
 * @property int|null $inviter_id
 * @property int|null $used_by
 * @property int $max_uses
 * @property Carbon|null $expires_at
 * @property Carbon|null $created_at
 * @property Carbon|null $used_at
 * @property-read User|null $inviter
 * @property-read User|null $user
 *
 * @method static \Illuminate\Database\Eloquent\Builder<static>|Invite newModelQuery()
 * @method static \Illuminate\Database\Eloquent\Builder<static>|Invite newQuery()
 * @method static \Illuminate\Database\Eloquent\Builder<static>|Invite query()
 * @method static \Illuminate\Database\Eloquent\Builder<static>|Invite whereCode($value)
 * @method static \Illuminate\Database\Eloquent\Builder<static>|Invite whereId($value)
 * @method static \Illuminate\Database\Eloquent\Builder<static>|Invite whereUsedBy($value)
 *
 * @mixin \Eloquent
 */
class Invite extends Model
{
    public $timestamps = false;

    protected $guarded = ['id'];

    protected $casts = [
        'expires_at' => 'datetime',
        'used_at' => 'datetime',
    ];

    /** @return BelongsTo<User, $this> */
    public function inviter(): BelongsTo
    {
        return $this->belongsTo(User::class, 'inviter_id');
    }

    /** @return BelongsTo<User, $this> */
    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class, 'used_by');
    }
}