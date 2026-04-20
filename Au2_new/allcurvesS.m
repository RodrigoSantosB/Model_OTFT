function Id = allcurvesS(co,Vv)

% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

global gp

Vtho = co(1);        
delta = co(2);       
n = co(3);            
l = co(4);              
lam = co(5);          
Vgcrit = co(6);        
Jth=co(7);
Rso = co(8);
Vtun=co(9);
V0 = co(10);
Rmax = co(11);
Idleak=gp(1);
phit = gp(2);
W = gp(3);
Vdsp(1) = gp(4);
Vdsp(2) = gp(5);
Vgsp(1) = gp(6);
Vgsp(2) = gp(7);
Vgsp(3) = gp(8);
typ=gp(9);
% display(sprintf('Vtho = %.2e', Vtho));
% display(sprintf('delta = %.2e', delta));
% display(sprintf('n = %.2e', n));
% display(sprintf('l = %.2e', l));
% display(sprintf('lam = %.2e', lam));
% display(sprintf('Vgcrit = %.2e', Vgcrit));
% display(sprintf('Jth = %.2e', Jth));
% display(sprintf('Rs = %.2e', Rs));

% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Model file
for i=1:5
    if i<3
        Vds = Vdsp(i);
        Vgs = Vv(:,i);
    else
        Vds = Vv(:,i);
        Vgs = Vgsp(i-2);
    end
    
    %Drain impact
    Vtp=Vtho+Vds.*delta;
    
    % Total charge (normalized)
    nphit=n*phit;
    theta=(Vgs-Vtp)./(nphit);
    qtot = log(1+exp(theta));
    
    % Fsat calculation - Long channel device
    Vgt = nphit*qtot;
    Vgn = 2*Vgt./(1+sqrt(2*Vgt./Vgcrit));
    x = Vds./Vgn;
    eta = 1-tanh(x);
    y = Vgn./phit;
    ll = (2*lam./(y.*y.*(1-eta.*eta))).*(exp(y.*(eta-1)).*(1-y.*eta)-(1-y));
    if Vds(1) == 0 ll(1) = lam; end;
    tau = 1./(1+ll);
    at = tau./(2-tau); % 1/(1+2*ll)
    Fsat = at.*(1 - exp(-Vds./phit))./(1 + at.*exp(-Vds./phit));
    Fsat(isnan(Fsat))=0;
    
    % Current calculation
    Jfree = Jth.*qtot.^l;
    
    % Final
    Idx = Idleak + W.*Jfree.*Fsat;
    
    
    % %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Vds -> Vdsi
    
    Idxx=Idleak;
    Rs = Rso + 0.5.*(Rmax-Rso).*(1-tanh((Vds-V0)./Vtun));
    Rd = Rso;
    dvg=Idx.*Rs;
    dvd=Idx.*Rd;
    count=1;
    
    while max(abs((Idx-Idxx)./Idx))>1e-10;
        count=count+1;
        if count>500, break, end
        
        Idxx=Idx;
        %dvg=(Idx.*Rs+dvg)/2;
        %dvd=(Idx.*Rd+dvd)/2; CHANGE
        %dvds=dvg+dvd;
        dvg=0.2*Idx.*Rs+0.8*dvg;
        dvd=0.2*Idx.*Rd+0.8*dvd;
        dvds=dvg+dvd;
        
        %Vdsi=Vds-dvds; CHANGE
        %Vgsi=Vgs-dvg;
        %Vdsi=max(Vds-dvds,0);
        %Vgsi=max(Vgs-dvg,0);
        if typ==-1
            Vdsi=Vds-dvds;     %p-type solution
            Vgsi=Vgs-dvg;
        else
            Vdsi=max(Vds-dvds,0);    %n-type solution
            Vgsi=max(Vgs-dvg,0);
        end
        %Drain impact
        Vtp=Vtho+Vdsi.*delta;
        
        % Total charge (normalized)
        nphit=n*phit;
        theta=(Vgsi-Vtp)./(nphit);
        qtot = log(1+exp(theta));
        
        % Fsat calculation - Long channel device
        Vgt = nphit*qtot;
        Vgn = 2*Vgt./(1+sqrt(2*Vgt./Vgcrit));
        x = Vdsi./Vgn;
        eta = 1-tanh(x);
        y = Vgn./phit;
        ll = (2*lam./(y.*y.*(1-eta.*eta))).*(exp(y.*(eta-1)).*(1-y.*eta)-(1-y));
        if Vdsi(1) < 1e-8 ll(1) = lam; end;
        tau = 1./(1+ll);
        at = tau./(2-tau); % 1/(1+2*ll)
        Fsat = at.*(1 - exp(-Vdsi./phit))./(1 + at.*exp(-Vdsi./phit));
        Fsat(isnan(Fsat))=0;
        
        % Current calculation
        Jfree = Jth.*qtot.^l;
        
        % Final
        Idx = Idleak + W.*Jfree.*Fsat;
        
    end
    
    % %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    % Wrapping up
    if i<3
        Id(:,i) = log10(Idx);
    else
        Id(:,i) = Idx*1e6;
    end
end

% any(~isfinite(Id))
% length(Id)

end