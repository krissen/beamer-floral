# The engine is the krissen/tikz-flora fork (branch beamer-floral). Point
# TIKZFLORA at a checkout, or set it in a local, untracked .env; without it
# the installed tikzflora is used.
if (-f '.env') {
  open my $fh, '<', '.env' or die "cannot read .env: $!";
  while (<$fh>) {
    chomp;
    next if /^\s*(?:#|$)/;
    $ENV{$1} = $2 if /^\s*([A-Za-z_]\w*)\s*=\s*(.*?)\s*$/;
  }
  close $fh;
}

if (my $flora = $ENV{'TIKZFLORA'}) {
  $ENV{'TEXINPUTS'} = "$flora/tex//:" . (defined $ENV{'TEXINPUTS'} ? $ENV{'TEXINPUTS'} : '');
  $ENV{'FLORA_LUA'} = "$flora/lua";
}
