<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('invites', function (Blueprint $table) {
            $table->id();
            $table->string('code', 32)->unique();
            $table->integer('inviter_id')->nullable();
            $table->integer('used_by')->nullable();
            $table->integer('max_uses')->default(1);
            $table->timestamp('expires_at')->nullable();
            $table->timestamp('created_at')->useCurrent();
            $table->timestamp('used_at')->nullable();

            $table->foreign('inviter_id')->references('id')->on('users')->nullOnDelete();
            $table->foreign('used_by')->references('id')->on('users')->nullOnDelete();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('invites');
    }
};