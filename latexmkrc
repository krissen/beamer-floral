# The engine is the krissen/tikz-flora fork (branch beamer-floral). Point
# TIKZFLORA at a checkout, or set it in a local, untracked .env; without it
# the installed tikzflora is used.
if (-f '.env') {
  open my $fh, '<', '.env' or die "cannot read .env: $!";
  while (<$fh>) {
    chomp;
    next if /^\s*(?:#|$)/;
    next unless /^\s*([A-Za-z_]\w*)\s*=\s*(.*?)\s*$/;
    my ($key, $value) = ($1, $2);
    $value =~ s/^(['"])(.*)\1$/$2/;
    $ENV{$key} = $value;
  }
  close $fh;
}

if (my $flora = $ENV{'TIKZFLORA'}) {
  $ENV{'TEXINPUTS'} = "$flora/tex//:" . (defined $ENV{'TEXINPUTS'} ? $ENV{'TEXINPUTS'} : '');
  $ENV{'FLORA_LUA'} = "$flora/lua";
}
